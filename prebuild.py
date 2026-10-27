"""Runs before buildozer in CI: puts libusque.so and libhev-socks5-tunnel.so into libs/arm64-v8a/."""
import io, json, os, shutil, subprocess, sys, tarfile, tempfile, urllib.request, zipfile

OUT = "libs/arm64-v8a"
os.makedirs(OUT, exist_ok=True)


def run(cmd, **kw):
    print("+", cmd, flush=True)
    subprocess.check_call(cmd, shell=True, **kw)


# ---- 1) usque (prebuilt android arm64 from the official release)
if not os.path.exists(f"{OUT}/libusque.so"):
    hdr = {"User-Agent": "aminium-build"}
    if os.environ.get("GH_TOKEN"):
        hdr["Authorization"] = "Bearer " + os.environ["GH_TOKEN"]
    rel = json.load(urllib.request.urlopen(urllib.request.Request(
        "https://api.github.com/repos/Diniboy1123/usque/releases/latest", headers=hdr)))
    names = [a["name"] for a in rel["assets"]]
    cand = [a for a in rel["assets"] if "android" in a["name"].lower() and "arm64" in a["name"].lower()]
    if not cand:
        sys.exit("No android+arm64 asset in usque release. Assets: " + ", ".join(names))
    a = cand[0]
    print("usque asset:", a["name"], flush=True)
    data = urllib.request.urlopen(a["browser_download_url"]).read()
    blob = None
    if a["name"].endswith(".zip"):
        z = zipfile.ZipFile(io.BytesIO(data))
        pick = [n for n in z.namelist() if os.path.basename(n).lower() == "usque"]
        blob = z.read(pick[0]) if pick else None
    elif ".tar" in a["name"] or a["name"].endswith(".tgz"):
        t = tarfile.open(fileobj=io.BytesIO(data))
        pick = [m for m in t.getmembers() if m.isfile() and os.path.basename(m.name).lower() == "usque"]
        blob = t.extractfile(pick[0]).read() if pick else None
    else:
        blob = data
    if not blob:
        sys.exit("Could not find the 'usque' binary inside " + a["name"])
    open(f"{OUT}/libusque.so", "wb").write(blob)
    print("libusque.so written:", len(blob), "bytes", flush=True)

# ---- 2) tun2socks (hev-socks5-tunnel), built with the NDK already on the GitHub runner
if not os.path.exists(f"{OUT}/libhev-socks5-tunnel.so"):
    ndk = (os.environ.get("ANDROID_NDK_HOME") or os.environ.get("ANDROID_NDK_LATEST_HOME")
           or os.environ.get("ANDROID_NDK_ROOT"))
    if not ndk:
        sys.exit("NDK not found (ANDROID_NDK_HOME is empty)")
    w = tempfile.mkdtemp(); os.makedirs(w + "/jni")
    run("git clone --recursive https://github.com/heiher/hev-socks5-tunnel", cwd=w + "/jni")
    open(w + "/jni/Android.mk", "w").write("include $(call all-subdir-makefiles)\n")
    open(w + "/jni/Application.mk", "w").write("APP_ABI := arm64-v8a\nAPP_PLATFORM := android-24\nAPP_OPTIM := release\n")
    run(f'"{ndk}/ndk-build" NDK_PROJECT_PATH=. APP_BUILD_SCRIPT=jni/Android.mk '
        f'NDK_APPLICATION_MK=jni/Application.mk -j4', cwd=w)
    shutil.copy(w + "/libs/arm64-v8a/libhev-socks5-tunnel.so", OUT)

print("libs ready:", os.listdir(OUT), flush=True)
