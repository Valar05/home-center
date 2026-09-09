#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
GEN=ROOT/'tools'/'venice_fleshpunk_phone.sh'
ENTRY=ROOT/'tools'/'fortress_image_entry.sh'
INSTALL=ROOT/'tools'/'install_fortress_image_phone.sh'
ACCEPT=ROOT/'tools'/'accept_fortress_image_phone.sh'
CAMPAIGN=ROOT/'tools'/'improper_image_delivery_campaign.sh'
SSH_AXIS=ROOT/'tools'/'ssh_axis.py'
RESOLVER=ROOT/'tools'/'resolve_cauldron_ssh.py'
DOC=ROOT/'docs'/'IMPROPER_IMAGE_DELIVERY_CAMPAIGN.md'
RELAY_TEST=ROOT/'tools'/'test_phone_relay_shizuku_independence.py'


def require(text, needle, owner):
    if needle not in text:
        raise AssertionError(f'{owner} missing required contract fragment: {needle!r}')


def forbid(text, needle, owner):
    if needle in text:
        raise AssertionError(f'{owner} contains forbidden fragment: {needle!r}')


def main():
    for shell in (GEN,ENTRY,INSTALL,ACCEPT,CAMPAIGN):
        subprocess.run(['bash','-n',str(shell)],check=True)
    subprocess.run([sys.executable,'-m','py_compile',str(SSH_AXIS),str(RESOLVER)],check=True)
    subprocess.run([sys.executable,str(RELAY_TEST)],check=True)

    gen=GEN.read_text()
    entry=ENTRY.read_text()
    install=INSTALL.read_text()
    accept=ACCEPT.read_text()
    campaign=CAMPAIGN.read_text()
    resolver=RESOLVER.read_text()
    doc=DOC.read_text()

    for fragment in (
        "FORTRESS_IMAGE_PROFILE:-fleshpunk",
        "fleshpunk|plain",
        "http://127.0.0.1:8188",
        "v1-5-pruned-emaonly.safetensors",
        "drw_fleshpunk_v1.safetensors",
        "publicPhonePath",
        "publicPhoneSha256",
        "/storage/emulated/0/Pictures/Fortress",
        "receipt mismatch",
        "public image final readback mismatch",
    ):
        require(gen,fragment,'generator')
    forbid(gen,'100.68.37.106','generator')
    forbid(gen,'0.0.0.0:8188','generator')

    for fragment in (
        'ssh_axis.py',
        'resolve_cauldron_ssh.py',
        'FORTRESS_CAULDRON_SSH',
        'THECAULDRON could not be resolved without Shizuku',
    ):
        require(entry,fragment,'image entry')

    for fragment in (
        'fortress-image',
        'fortress-image-accept',
        'fortress-image-ui',
        'Improper Image',
        'Pictures/Fortress',
        'export FORTRESS_IMAGE_PROFILE=fleshpunk',
        "DEST=\"$HOME/.local/share/fortress-image\"",
        "'shizukuRequired':False",
        "'atomRequired':False",
        "'vladRequired':False",
    ):
        require(install,fragment,'standalone image installer')
    for forbidden in (
        'setup_vlad_swarm_daemon.sh',
        'judgment-jars',
        'server.mjs',
        '.local/share/atom',
    ):
        forbid(install,forbidden,'standalone image installer')

    for fragment in (
        'fortress-image-phone-acceptance.v1',
        'public Pictures PNG SHA-256 does not match returned phone bytes',
        'drewPerceptualAccepted',
        'plain profile unexpectedly loaded a LoRA',
        'drw_fleshpunk_v1.safetensors',
        "'shizukuRequired':False",
        "'atomRequired':False",
        "'uiRequired':False",
    ):
        require(accept,fragment,'acceptance')
    forbid(accept,'ATOM_NOT_INSTALLED','acceptance')

    require(campaign,'install_fortress_image_phone.sh','campaign')
    forbid(campaign,'install_atom_phone.sh','campaign')
    require(campaign,'fortress-image-accept','campaign')
    require(campaign,'IMPROPER_IMAGE_CAMPAIGN ACCEPTED','campaign')
    require(campaign,'publicPicturesArtifactDelivered','campaign')

    for forbidden in ('run_rish','moe.shizuku','wifi_reconnect','192.168.40.213'):
        forbid(resolver,forbidden,'THECAULDRON resolver')
    for fragment in ('tailscale','verified-cache','lan-scan',"'shizukuRequired': False"):
        require(resolver,fragment,'THECAULDRON resolver')

    for fragment in (
        'Prompt authored, image rendered, image delivered, and user kept are separate states',
        'unversioned remote runtime file',
        'Do not call repository code “deployed.”',
        'Do not make Drew manually run a repair script',
        'Shizuku is not load-bearing',
        'notification/open action is best-effort',
        'standalone image runtime',
        'GitHub control-plane fallback',
    ):
        require(doc,fragment,'campaign documentation')

    print('IMPROPER_IMAGE_DELIVERY_CONTRACT_OK')


if __name__=='__main__':
    main()
