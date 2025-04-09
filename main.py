import requests
import time
import os

print("📂 current working directory:", os.getcwd())

def get_rps_ticket(refresh_token):
    url = "https://login.live.com/oauth20_token.srf"
    data = {
        "client_id": "00000000402b5328",
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
        "redirect_uri": "https://login.live.com/oauth20_desktop.srf",
        "scope": "service::user.auth.xboxlive.com::MBI_SSL"
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    res = requests.post(url, headers=headers, data=data)
    res.raise_for_status()
    return res.json()["access_token"]

def get_xbl_token(rps_ticket):
    url = "https://user.auth.xboxlive.com/user/authenticate"
    headers = {
        "Content-Type": "application/json",
        "x-xbl-contract-version": "0"
    }
    body = {
        "Properties": {
            "AuthMethod": "RPS",
            "SiteName": "user.auth.xboxlive.com",
            "RpsTicket": rps_ticket
        },
        "RelyingParty": "http://auth.xboxlive.com",
        "TokenType": "JWT"
    }
    res = requests.post(url, headers=headers, json=body)
    res.raise_for_status()
    json_res = res.json()
    return json_res["Token"], json_res["DisplayClaims"]["xui"][0]["uhs"]

def get_xsts_token(user_token):
    url = "https://xsts.auth.xboxlive.com/xsts/authorize"
    headers = {
        "Content-Type": "application/json",
        "x-xbl-contract-version": "1"
    }
    body = {
        "Properties": {
            "SandboxId": "RETAIL",
            "UserTokens": [user_token]
        },
        "RelyingParty": "rp://api.minecraftservices.com/",
        "TokenType": "JWT"
    }

    while True:
        try:
            res = requests.post(url, headers=headers, json=body)
            res.raise_for_status()
            return res.json()["Token"]
        except requests.exceptions.ConnectionError as e:
            if "getaddrinfo failed" in str(e):
                print("🌐 DNS error (xsts), retry in 5 seconds...")
                time.sleep(5)
                continue
            raise e

def login_minecraft(uhs, xsts_token):
    url = "https://api.minecraftservices.com/authentication/login_with_xbox"
    headers = {"Content-Type": "application/json"}
    identity_token = f"XBL3.0 x={uhs};{xsts_token}"
    body = {"identityToken": identity_token}

    while True:
        try:
            res = requests.post(url, headers=headers, json=body)
            if res.status_code == 429:
                print("🚫 rate limit (429), retry in 5 seconds...")
                time.sleep(5)
                continue
            res.raise_for_status()
            return res.json()["access_token"]
        except requests.exceptions.ConnectionError as e:
            if "getaddrinfo failed" in str(e):
                print("🌐 DNS error (minecraft), retry in 5 seconds...")
                time.sleep(5)
                continue
            raise e

# === batch main process ===
with open("RefreshToken.txt", "r", encoding="utf-8") as infile, \
     open("result.txt", "w", encoding="utf-8") as outfile, \
     open("error.txt", "w", encoding="utf-8") as errfile:

    for idx, line in enumerate(infile):
        refresh_token = line.strip()
        if not refresh_token:
            continue

        print(f"\n▶️ processing the {idx+1}th Refresh Token...")

        try:
            rps = get_rps_ticket(refresh_token)
            xbl, uhs = get_xbl_token(rps)
            xsts = get_xsts_token(xbl)
            mc_token = login_minecraft(uhs, xsts)

            print(f"✅ the {idx+1}th success! write the Access Token (first 30 characters): {mc_token[:30]}...")
            outfile.write(mc_token + "\n")
            outfile.flush()

        except Exception as e:
            print(f"❌ the {idx+1}th failed: {e}")
            errfile.write(refresh_token + "\n")
            errfile.flush()
            continue

        print("⏸️ pause for 3 seconds...\n")
        time.sleep(3)
