"""Generate a self-signed SSL certificate so the app can run over HTTPS locally.

Needed for getUserMedia camera access from a phone on your LAN (browsers only
allow camera access on "secure contexts" = HTTPS or localhost).

Usage:
    python scripts/gen_cert.py [your-lan-ip]

Then start the app over HTTPS:
    $env:SSL_CERTFILE='certs/cert.pem'
    $env:SSL_KEYFILE='certs/key.pem'
    python app.py

And open https://<your-lan-ip>:5000 on the phone (accept the cert warning once).
"""
import socket
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CERT_DIR = ROOT / "certs"


def _lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def main():
    ip = sys.argv[1] if len(sys.argv) > 1 else _lan_ip()
    CERT_DIR.mkdir(exist_ok=True)
    cert = CERT_DIR / "cert.pem"
    key = CERT_DIR / "key.pem"

    cmd = [
        "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
        "-keyout", str(key), "-out", str(cert), "-days", "365",
        "-subj", "/CN=socialai-dev",
        "-addext", f"subjectAltName=IP:{ip},DNS:localhost",
    ]
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)

    print(f"\nCertificate: {cert}")
    print(f"Key        : {key}")
    print()
    print("Start HTTPS with:")
    print(f"  $env:SSL_CERTFILE='certs/cert.pem'")
    print(f"  $env:SSL_KEYFILE='certs/key.pem'")
    print("  python app.py")
    print(f"\nThen open https://{ip}:5000 on the phone and accept the cert warning.")


if __name__ == "__main__":
    main()