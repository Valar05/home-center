# Git-pinned Ritsu Control v0.17 Android cutover campaign.
# Run only in disposable checkout; deterministic receipts, no cloud CI.
param([ValidateSet('doctor','build','status')][string]$Mode='doctor')
$ErrorActionPreference='Stop'
$root=Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$proof=Join-Path $env:LOCALAPPDATA 'RitsuControlBridge\LocalLink\android-v017'
[IO.Directory]::CreateDirectory($proof)|Out-Null
$receipt=Join-Path $proof 'build-receipt.json'
$log=Join-Path $proof 'gradle-build.log'
$sha=(& git -C $root rev-parse HEAD).Trim()
$expected=$env:RITSU_CAMPAIGN_PIN_SHA
if($expected -and $sha -ne $expected){throw 'Pinned Git source mismatch'}
$android=Join-Path $root 'android\ritsu-control'
$manifest=Join-Path $android 'app\src\main\AndroidManifest.xml'
$app=Join-Path $android 'app\src\main\java\com\homecenter\ritsucontrol'
$local=Join-Path $app 'RitsuLocalSync.java'
$service=Join-Path $app 'RitsuControlService.java'
$activity=Join-Path $app 'MainActivity.java'
$gradle='C:\Users\dclar\.gradle\wrapper\dists\gradle-8.11.1-bin\bpt9gzteqjrbo1mjrsomdt32c\gradle-8.11.1\bin\gradle.bat'
$env:ANDROID_HOME=Join-Path $env:LOCALAPPDATA 'Android\Sdk'
$env:ANDROID_SDK_ROOT=$env:ANDROID_HOME
$apk=Join-Path $android 'app\build\outputs\apk\debug\app-debug.apk'
$named=Join-Path $proof 'Ritsu-Control-v0.17.0-Local-Streaming.apk'
function SaveReceipt($state,$detail){
 $info=[ordered]@{campaign='ritsu-local-android-v017';state=$state;detail=$detail;sourceSha=$sha;apk=$named;sha256=$(if(Test-Path $named){(Get-FileHash $named -Algorithm SHA256).Hash.ToLower()}else{''});size=$(if(Test-Path $named){(Get-Item $named).Length}else{0});timestampUTC=(Get-Date).ToUniversalTime().ToString('o')}
 $tmp=$receipt+'.tmp'
 [IO.File]::WriteAllText($tmp,($info|ConvertTo-Json),[Text.UTF8Encoding]::new($false))
 Move-Item -Force $tmp $receipt
 $info|ConvertTo-Json -Compress
}
if($Mode -eq 'status'){
 if(Test-Path $receipt){Get-Content $receipt}else{'RITSU_BUILD_STATUS=unstarted'}
 exit 0
}
foreach($file in @($manifest,$local,$service,$activity,$gradle)){
 if(!(Test-Path $file)){throw "Required source missing: $file"}
}
if(!(Test-Path (Join-Path $env:ANDROID_HOME 'platforms\android-35'))){throw 'Android SDK35 missing'}
if(!(Test-Path $gradle)){throw 'Pinned Gradle 8.11.1 missing'}
$activityText=[IO.File]::ReadAllText($activity)
$serviceText=[IO.File]::ReadAllText($service)
if($activityText.Contains('HomeCenterCloudPairing') -or $activityText.Contains('acceptHomeCenterOAuth(getIntent())')){throw 'Cloud UI call remains'}
if(!$activityText.Contains('"LOCAL_QUEUED"') -or !$serviceText.Contains('new RitsuLocalSync')){throw 'Direct conversation wiring missing'}
if(!$serviceText.Contains('complete,"LOCAL_QUEUED"')){throw 'Voice path still cloud-linked'}
if(!([IO.File]::ReadAllText($manifest).Contains('ritsu_local_network_security'))){throw 'Pinned network policy absent'}
if($Mode -eq 'doctor'){SaveReceipt 'doctor_pass' 'build prerequisites verified';exit 0}
[IO.File]::WriteAllText((Join-Path $android 'local.properties'),'sdk.dir=C:/Users/dclar/AppData/Local/Android/Sdk')
& $gradle -p $android :app:testDebugUnitTest :app:assembleDebug '-PritsuStableInstall=true' --no-daemon *> $log
if($LASTEXITCODE -ne 0){SaveReceipt 'failed' 'Gradle failed; inspect gradle-build.log';exit 1}
if(!(Test-Path $apk)){SaveReceipt 'failed' 'APK not produced';exit 2}
$aapt=Join-Path $env:ANDROID_HOME 'build-tools\35.0.0\aapt.exe'
$signer=Join-Path $env:ANDROID_HOME 'build-tools\35.0.0\apksigner.bat'
$badging=(& $aapt dump badging $apk | Select-String '^package:').ToString()
if($badging -notmatch "name='com\.homecenter\.ritsucontrol\.live'" -or $badging -notmatch "versionCode='18'"){SaveReceipt 'failed' 'Wrong package identity';exit 3}
& $signer verify $apk
if($LASTEXITCODE -ne 0){SaveReceipt 'failed' 'Signature verify failed';exit 4}
Copy-Item -Force $apk $named
SaveReceipt 'build_pass' $badging
