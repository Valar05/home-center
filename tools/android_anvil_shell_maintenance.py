#!/data/data/com.termux/files/usr/bin/python
"""Typed Anvil Shell phone maintenance executor.

The caller supplies identity and one immutable source commit. Repository, source
subdirectory, build tasks, package id, install behavior, and readback behavior
are fixed here. There is deliberately no command, argv, URL, or path input.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import time
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

REQUEST_SCHEMA = "phone.maintenance.anvil-shell.v1"
RECEIPT_SCHEMA = "phone.maintenance.anvil-shell.receipt.v1"
OPERATION = "anvil_shell.build_install.v1"
REPOSITORY = "Valar05/continue-continue"
REPOSITORY_URL = "https://github.com/Valar05/continue-continue.git"
SOURCE_SUBDIR = "edge/android-shell"
PACKAGE_ID = "com.continuecontinue.anvilshell"
VERSION_NAME = "0.1.0-checkpoint"
REQUEST_KEYS = {
    "action","schema","operation","automaticReplay","deviceId","packageId","workerId",
    "queueDocId","queueRevision","commissionHash","laneId","sessionId","approvalId",
    "leaseId","sourceRepository","sourceHead","sourceSubdir","expectedVersionName",
    "expectedSignerSha256","timeoutSeconds","networkPolicy","rollbackPolicy",
}
ROOT = Path(os.environ.get("HOME_CENTER_PHONE_ANVIL_ROOT", str(Path.home()/".home-center"/"anvil-shell-maintenance")))
LOG_LIMIT = 12000
GRADLE_URL = "https://services.gradle.org/distributions/gradle-8.13-bin.zip"
GRADLE_SHA256 = "20f1b1176237254a6fc204d8434196fa11a4cfb387567519c61556e8710aed78"
PLATFORM_URL = "https://dl.google.com/android/repository/platform-36_r02.zip"
PLATFORM_SHA256 = "37607369a28c5b640b3a7998868d45898ebcb777565a0e85f9acf36f29631d2e"
FIXED_TERMUX_PACKAGES = ("git","openjdk-21","aapt","apksigner","unzip")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",",":")).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda:handle.read(1024*1024),b""):
            h.update(block)
    return h.hexdigest()


def run(argv: list[str], *, cwd: Path|None=None, timeout: int=120, check: bool=True, env: dict[str,str]|None=None) -> dict[str,Any]:
    started=time.monotonic_ns()
    proc=subprocess.run(argv,cwd=str(cwd) if cwd else None,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout,env=env)
    result={"argvIdentity":[Path(argv[0]).name,*argv[1:]],"exit":proc.returncode,"outputTail":proc.stdout[-LOG_LIMIT:],"elapsedMs":(time.monotonic_ns()-started)//1_000_000}
    if check and proc.returncode:
        raise RuntimeError(f"{Path(argv[0]).name} failed ({proc.returncode}): {proc.stdout[-2000:]}")
    return result


def required(action: dict[str,Any], key: str) -> str:
    value=action.get(key)
    if not isinstance(value,str) or not value.strip():
        raise ValueError(f"anvil maintenance requires {key}")
    return value.strip()


def validate(action: dict[str,Any]) -> None:
    if set(action)-REQUEST_KEYS:
        raise ValueError("anvil maintenance rejects unknown fields")
    fixed={
        "action":"anvil_shell_build_install","schema":REQUEST_SCHEMA,"operation":OPERATION,
        "deviceId":"primary-phone","packageId":PACKAGE_ID,"workerId":"phone-relay:primary-phone",
        "laneId":"PHONE_MAINTENANCE","sourceRepository":REPOSITORY,
        "sourceSubdir":SOURCE_SUBDIR,"expectedVersionName":VERSION_NAME,
        "networkPolicy":"bootstrap-and-build","rollbackPolicy":"retain_previous_apk_if_present",
    }
    for key,value in fixed.items():
        if action.get(key)!=value:
            raise PermissionError(f"anvil maintenance {key} identity mismatch")
    if action.get("automaticReplay") is not False:
        raise PermissionError("anvil maintenance automatic replay must remain disabled")
    for key in ("queueDocId","queueRevision","commissionHash","sessionId","approvalId","leaseId","sourceHead"):
        required(action,key)
    if not re.fullmatch(r"[0-9a-f]{64}",action["commissionHash"]):
        raise ValueError("commissionHash must be SHA-256")
    if not re.fullmatch(r"[0-9a-f]{40}",action["sourceHead"]):
        raise ValueError("sourceHead must be a full commit SHA")
    expected=action.get("expectedSignerSha256")
    if expected and (not isinstance(expected,str) or not re.fullmatch(r"[0-9a-f]{64}",expected)):
        raise ValueError("expectedSignerSha256 must be SHA-256")
    timeout=action.get("timeoutSeconds")
    if not isinstance(timeout,int) or isinstance(timeout,bool) or not 60<=timeout<=3600:
        raise ValueError("timeoutSeconds must be 60..3600")


def version(argv: list[str]) -> str:
    try:
        return run(argv,timeout=20,check=False)["outputTail"].splitlines()[0][:500]
    except Exception as exc:
        return f"UNAVAILABLE:{type(exc).__name__}"


def download_verified(url: str, expected_sha256: str, target: Path) -> dict[str,Any]:
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.is_file() and sha256_file(target)==expected_sha256:
        return {"urlIdentity":url.rsplit("/",1)[-1],"sha256":expected_sha256,"bytes":target.stat().st_size,"reused":True}
    partial=target.with_suffix(target.suffix+".partial")
    h=hashlib.sha256()
    size=0
    with urllib.request.urlopen(url,timeout=60) as response, partial.open("wb") as handle:
        while True:
            block=response.read(1024*1024)
            if not block:
                break
            handle.write(block); h.update(block); size+=len(block)
    actual=h.hexdigest()
    if actual!=expected_sha256:
        partial.unlink(missing_ok=True)
        raise RuntimeError(f"fixed toolchain archive hash mismatch for {url.rsplit('/',1)[-1]}")
    os.replace(partial,target)
    return {"urlIdentity":url.rsplit("/",1)[-1],"sha256":actual,"bytes":size,"reused":False}


def safe_extract(archive: Path, target: Path) -> None:
    target.mkdir(parents=True,exist_ok=True)
    root=target.resolve()
    with zipfile.ZipFile(archive) as zf:
        for info in zf.infolist():
            candidate=(target/info.filename).resolve()
            if os.path.commonpath((str(root),str(candidate)))!=str(root):
                raise RuntimeError("toolchain archive contains path traversal")
        zf.extractall(target)


def ensure_toolchain(timeout: int) -> tuple[Path,Path,dict[str,Any]]:
    ROOT.mkdir(parents=True,exist_ok=True)
    bootstrap=[]
    needed=("git","java","aapt2","apksigner","unzip")
    if any(not shutil.which(name) for name in needed):
        pkg=shutil.which("pkg")
        if not pkg:
            raise RuntimeError("fixed Termux package bootstrap is unavailable")
        bootstrap.append(run([pkg,"install","-y",*FIXED_TERMUX_PACKAGES],timeout=timeout))
    missing=[name for name in needed if not shutil.which(name)]
    if missing:
        raise RuntimeError("fixed Termux package bootstrap did not provide: "+",".join(missing))
    downloads=ROOT/"downloads"
    toolchains=ROOT/"toolchains"
    gradle_archive=downloads/"gradle-8.13-bin.zip"
    gradle_receipt=download_verified(GRADLE_URL,GRADLE_SHA256,gradle_archive)
    gradle_home=toolchains/"gradle-8.13"
    gradle=gradle_home/"bin"/"gradle"
    if not gradle.is_file():
        staging=toolchains/"gradle-staging"
        if staging.exists(): shutil.rmtree(staging)
        safe_extract(gradle_archive,staging)
        unpacked=staging/"gradle-8.13"
        if not unpacked.is_dir(): raise RuntimeError("verified Gradle archive layout mismatch")
        gradle_home.parent.mkdir(parents=True,exist_ok=True)
        if gradle_home.exists(): shutil.rmtree(gradle_home)
        os.replace(unpacked,gradle_home)
        shutil.rmtree(staging)
    android_home=toolchains/"android-sdk"
    platform=android_home/"platforms"/"android-36"
    platform_archive=downloads/"platform-36_r02.zip"
    platform_receipt=download_verified(PLATFORM_URL,PLATFORM_SHA256,platform_archive)
    if not (platform/"android.jar").is_file():
        staging=toolchains/"platform-staging"
        if staging.exists(): shutil.rmtree(staging)
        safe_extract(platform_archive,staging)
        unpacked=staging/"android-36"
        if not (unpacked/"android.jar").is_file(): raise RuntimeError("verified Android platform archive layout mismatch")
        platform.parent.mkdir(parents=True,exist_ok=True)
        if platform.exists(): shutil.rmtree(platform)
        os.replace(unpacked,platform)
        shutil.rmtree(staging)
    package_receipt=run([shutil.which("dpkg") or "dpkg","-s",*FIXED_TERMUX_PACKAGES],timeout=60,check=False)
    return gradle,android_home,{
        "fixedPackages":list(FIXED_TERMUX_PACKAGES),
        "packageMetadataDigest":hashlib.sha256(package_receipt["outputTail"].encode()).hexdigest(),
        "bootstrapRan":bool(bootstrap),
        "bootstrapOutputDigests":[hashlib.sha256(item["outputTail"].encode()).hexdigest() for item in bootstrap],
        "gradleArchive":gradle_receipt,
        "androidPlatformArchive":platform_receipt,
    }


def signer_sha256(apk: Path) -> tuple[str,str]:
    tool=shutil.which("apksigner")
    if not tool:
        raise RuntimeError("apksigner is required for signer readback")
    out=run([tool,"verify","--print-certs",str(apk)],timeout=60)["outputTail"]
    match=re.search(r"Signer #1 certificate SHA-256 digest:\s*([0-9a-fA-F]{64})",out)
    if not match:
        raise RuntimeError("apksigner did not report a SHA-256 signer digest")
    return match.group(1).lower(),out


def installed_info() -> dict[str,Any]:
    pm=shutil.which("pm") or "/system/bin/pm"
    path_result=run([pm,"path",PACKAGE_ID],timeout=30,check=False)
    paths=[line.split(":",1)[1].strip() for line in path_result["outputTail"].splitlines() if line.startswith("package:")]
    dump=run([pm,"dump",PACKAGE_ID],timeout=60,check=False)["outputTail"]
    version_name=""
    version_code=""
    for line in dump.splitlines():
        stripped=line.strip()
        if stripped.startswith("versionName=") and not version_name:
            version_name=stripped.split("=",1)[1].strip()
        if stripped.startswith("versionCode=") and not version_code:
            version_code=stripped.split("=",1)[1].split()[0].strip()
    return {"paths":paths,"versionName":version_name,"versionCode":version_code,"dumpDigest":hashlib.sha256(dump.encode()).hexdigest()}


def readable_installed_hash(paths: list[str]) -> str:
    for raw in paths:
        path=Path(raw)
        try:
            if path.is_file():
                return sha256_file(path)
        except (OSError,PermissionError):
            pass
        rish=shutil.which("rish")
        if rish and re.fullmatch(r"/data/app/[A-Za-z0-9_./=+~-]+\.apk",raw):
            probe=run([rish,"-c",f"sha256sum {raw}"],timeout=60,check=False)["outputTail"]
            match=re.search(r"\b([0-9a-f]{64})\b",probe)
            if match:
                return match.group(1)
    return ""


def prepare_source(head: str, timeout: int) -> tuple[Path,dict[str,Any]]:
    checkout=ROOT/"source"
    ROOT.mkdir(parents=True,exist_ok=True)
    if not (checkout/".git").is_dir():
        if checkout.exists():
            shutil.rmtree(checkout)
        checkout.mkdir(parents=True)
        run([shutil.which("git") or "git","init"],cwd=checkout,timeout=60)
        run([shutil.which("git") or "git","remote","add","origin",REPOSITORY_URL],cwd=checkout,timeout=30)
    fetch=run([shutil.which("git") or "git","fetch","--depth","1","origin",head],cwd=checkout,timeout=timeout)
    run([shutil.which("git") or "git","checkout","--detach","--force","FETCH_HEAD"],cwd=checkout,timeout=60)
    actual=run([shutil.which("git") or "git","rev-parse","HEAD"],cwd=checkout,timeout=30)["outputTail"].strip().splitlines()[-1]
    dirty=bool(run([shutil.which("git") or "git","status","--porcelain"],cwd=checkout,timeout=30)["outputTail"].strip())
    if actual!=head or dirty:
        raise RuntimeError("phone source checkout identity or cleanliness mismatch")
    return checkout,{"fetch":fetch,"actualHead":actual,"dirty":dirty}


def install_apk(apk: Path, source_head: str, timeout: int) -> tuple[dict[str,Any],str]:
    pm=shutil.which("pm") or "/system/bin/pm"
    attempts=[]
    direct=run([pm,"install","-r",str(apk)],timeout=timeout,check=False)
    attempts.append(("pm",direct))
    if direct["exit"]==0 and "Success" in direct["outputTail"]:
        return direct,"pm"
    rish=shutil.which("rish")
    downloads=Path.home()/"storage"/"downloads"
    if rish and downloads.is_dir():
        shared=downloads/f"AnvilShell-{source_head}.apk"
        shutil.copy2(apk,shared)
        resolved=str(shared.resolve())
        if not re.fullmatch(r"/storage/emulated/[0-9]+/Download/AnvilShell-[0-9a-f]{40}\.apk",resolved):
            raise RuntimeError("fixed shared installer path resolved outside the allowlist")
        elevated=run([rish,"-c",f"pm install -r --user 0 {resolved}"],timeout=timeout,check=False)
        attempts.append(("rish-pm",elevated))
        if elevated["exit"]==0 and "Success" in elevated["outputTail"]:
            return elevated,"rish-pm"
    adb=shutil.which("adb")
    if adb:
        fallback=run([adb,"install","-r",str(apk)],timeout=timeout,check=False)
        attempts.append(("adb",fallback))
        if fallback["exit"]==0 and "Success" in fallback["outputTail"]:
            return fallback,"adb"
    detail="\n".join(f"{name}: {result['outputTail'][-800:]}" for name,result in attempts)
    raise RuntimeError("fixed Anvil install strategies failed: "+detail[-2400:])


def execute(action: dict[str,Any]) -> dict[str,Any]:
    validate(action)
    started=time.time_ns()
    timeout=int(action["timeoutSeconds"])
    gradle,android_home,bootstrap=ensure_toolchain(timeout)
    checkout,source=prepare_source(action["sourceHead"],timeout)
    project=checkout/SOURCE_SUBDIR
    if not project.is_dir():
        raise RuntimeError("allowlisted Anvil source subdirectory is absent")
    build_env=dict(os.environ)
    build_env["ANDROID_HOME"]=str(android_home)
    build_env["ANDROID_SDK_ROOT"]=str(android_home)
    aapt2=shutil.which("aapt2")
    toolchain={
        "git":version([shutil.which("git") or "git","--version"]),
        "java":version([shutil.which("java") or "java","-version"]),
        "gradle":version([str(gradle),"--version"]),
        "aapt2":version([aapt2 or "aapt2","version"]),
        "apksigner":version([shutil.which("apksigner") or "apksigner","version"]),
        "androidHome":str(android_home),
        "bootstrap":bootstrap,
    }
    previous=installed_info()
    rollback_dir=ROOT/"rollback"
    rollback_dir.mkdir(parents=True,exist_ok=True)
    rollback={"policy":action["rollbackPolicy"],"previousPackageObserved":bool(previous["paths"]),"previousVersionName":previous["versionName"],"retained":False,"previousApkSha256":""}
    for raw in previous["paths"][:1]:
        try:
            prior=Path(raw)
            if prior.is_file():
                target=rollback_dir/f"{PACKAGE_ID}-{int(time.time())}.apk"
                shutil.copy2(prior,target)
                rollback.update({"retained":True,"previousApkSha256":sha256_file(target),"path":str(target)})
        except (OSError,PermissionError):
            pass
    build=run([str(gradle),"-p",str(project),f"-Pandroid.aapt2FromMavenOverride={aapt2}",":app:testDebugUnitTest",":app:assembleDebug","--no-daemon"],cwd=checkout,timeout=timeout,env=build_env)
    apk=project/"app"/"build"/"outputs"/"apk"/"debug"/"app-debug.apk"
    if not apk.is_file():
        raise RuntimeError("Anvil debug APK missing after successful build")
    apk_hash=sha256_file(apk)
    signer,signer_output=signer_sha256(apk)
    expected=action.get("expectedSignerSha256")
    if expected and signer!=expected:
        raise RuntimeError("Anvil APK signer does not match the approved signer digest")
    install,strategy=install_apk(apk,action["sourceHead"],timeout)
    installed=installed_info()
    installed_hash=readable_installed_hash(installed["paths"])
    if installed["versionName"]!=VERSION_NAME or not installed["paths"]:
        raise RuntimeError("Anvil package/version readback failed")
    if not installed_hash:
        raise RuntimeError("installed Anvil APK hash is unreadable; exact byte readback is required")
    if installed_hash!=apk_hash:
        raise RuntimeError("installed Anvil APK hash differs from the built APK")
    receipt={
        "schema":RECEIPT_SCHEMA,"operation":OPERATION,"requestHash":digest(action),
        "deviceId":action["deviceId"],"packageId":action["packageId"],"workerId":action["workerId"],
        "queueDocId":action["queueDocId"],"queueRevision":action["queueRevision"],
        "commissionHash":action["commissionHash"],"laneId":action["laneId"],"sessionId":action["sessionId"],
        "approvalId":action["approvalId"],"leaseId":action["leaseId"],
        "sourceRepository":action["sourceRepository"],"sourceHead":source["actualHead"],
        "sourceSubdir":action["sourceSubdir"],"expectedVersionName":action["expectedVersionName"],
        "automaticReplay":False,"networkUsed":True,"writeUsed":True,"subprocessUsed":True,
        "buildUsed":True,"installUsed":True,"uiUsed":False,"testsPassed":True,
        "buildExit":build["exit"],"installExit":install["exit"],"readbackVerified":True,
        "apkSha256":apk_hash,"apkBytes":apk.stat().st_size,"signerSha256":signer,
        "installedApkSha256":installed_hash,"installedPackageId":PACKAGE_ID,
        "installedVersionName":installed["versionName"],"installedVersionCode":installed["versionCode"],
        "installStrategy":strategy,"installedPaths":installed["paths"],"toolchain":toolchain,
        "rollback":rollback,"source":source,"buildLogDigest":hashlib.sha256(build["outputTail"].encode()).hexdigest(),
        "signerOutputDigest":hashlib.sha256(signer_output.encode()).hexdigest(),
        "installOutputDigest":hashlib.sha256(install["outputTail"].encode()).hexdigest(),
        "startedAtNs":str(started),"finishedAtNs":str(time.time_ns()),
        "status":"INSTALLED_READBACK_VERIFIED",
    }
    receipt["receiptHash"]=digest(receipt)
    return receipt
