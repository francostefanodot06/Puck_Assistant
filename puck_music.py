import requests
import subprocess
import argparse
import random
import sys
import os

NAVIDROME_URL = "http://TU_IP_NAVIDROME:4533"
USER = "TU_USUARIO"
TOKEN = "TU_TOKEN_NAVIDROME"
SALT = "TU_SALT"
CLIENT = "PuckAssistant"

def get_auth():
    return f"u={USER}&t={TOKEN}&s={SALT}&v=1.16.1&c={CLIENT}&f=json"

def main():
    parser = argparse.ArgumentParser(description="Controlador de música para Puck")
    parser.add_argument("query", nargs="*", help="Búsqueda de canción, álbum o playlist")
    parser.add_argument("--tipo", choices=["cancion", "album", "playlist"], default="cancion")
    parser.add_argument("--aleatorio", action="store_true", help="Activar modo aleatorio")
    parser.add_argument("--accion", choices=["play", "pause", "stop", "next", "previous", "volumen"], help="Acción multimedia")
    parser.add_argument("--valor", type=int, help="Valor para el volumen (0 a 100)")
    args = parser.parse_args()

    env = os.environ.copy()
    env["DISPLAY"] = ":0"
    env["WAYLAND_DISPLAY"] = "wayland-0"
    env["XDG_RUNTIME_DIR"] = f"/run/user/{os.getuid()}"

    # Control multimedia e intercepciones directas
    if args.accion:
        try:
            if args.accion == "volumen" and args.valor is not None:
                volumen_decimal = max(0.0, min(1.5, args.valor / 100.0))
                output = subprocess.check_output("wpctl status", shell=True).decode()
                encontrado = False

                for line in output.splitlines():
                    if "mpv" in line.lower() and "." in line:
                        partes = line.strip().split(".")
                        if partes and partes[0].isdigit():
                            mpv_id = partes[0]
                            subprocess.run(["wpctl", "set-volume", mpv_id, str(volumen_decimal)], check=True)
                            encontrado = True
                            break

                if not encontrado:
                    outputs_pactl = subprocess.check_output("pactl list sink-inputs short 2>/dev/null", shell=True).decode()
                    for line in outputs_pactl.splitlines():
                        if "mpv" in line.lower():
                            parts = line.split()
                            if parts:
                                client_id = parts[0]
                                subprocess.run(["pactl", "set-sink-input-volume", client_id, f"{args.valor}%"], check=True)
                                encontrado = True
                                break

                if encontrado:
                    print(f"Volumen de la música ajustado a {args.valor}%")
                else:
                    print("No hay música sonando de fondo para regular el volumen.")

            elif args.accion in ["pause", "stop"]:
                subprocess.run(["killall", "-q", "mpv"])
                print("Música detenida.")
            else:
                subprocess.run(["playerctl", "--player=mpv", args.accion], env=env)
                print(f"Acción ejecutada: {args.accion}")
        except Exception as e:
            print(f"Error al procesar la acción: {e}")
        return

    if not args.query:
        print("No se especificó qué reproducir.")
        sys.exit(1)

    query = " ".join(args.query)
    auth = get_auth()
    urls_to_play = []

    try:
        if args.tipo == "cancion":
            res = requests.get(f"{NAVIDROME_URL}/rest/search3.view?query={query}&songCount=10&{auth}").json()
            song = res['subsonic-response']['searchResult3']['song'][0]
            urls_to_play.append(f"{NAVIDROME_URL}/rest/stream.view?id={song['id']}&{auth}")
            print(f"Reproduciendo: {song['title']} - {song['artist']}")

        elif args.tipo == "album":
            res = requests.get(f"{NAVIDROME_URL}/rest/search3.view?query={query}&albumCount=1&{auth}").json()
            album_id = res['subsonic-response']['searchResult3']['album'][0]['id']
            album_data = requests.get(f"{NAVIDROME_URL}/rest/getAlbum.view?id={album_id}&{auth}").json()
            for song in album_data['subsonic-response']['album']['song']:
                urls_to_play.append(f"{NAVIDROME_URL}/rest/stream.view?id={song['id']}&{auth}")
            print(f"Reproduciendo Álbum")

        elif args.tipo == "playlist":
            res = requests.get(f"{NAVIDROME_URL}/rest/getPlaylists.view?{auth}").json()
            playlists = res['subsonic-response']['playlists'].get('playlist', [])
            matched = next((p for p in playlists if query.lower() in p['name'].lower()), None)
            if matched:
                pl_data = requests.get(f"{NAVIDROME_URL}/rest/getPlaylist.view?id={matched['id']}&{auth}").json()
                for song in pl_data['subsonic-response']['playlist']['entry']:
                    urls_to_play.append(f"{NAVIDROME_URL}/rest/stream.view?id={song['id']}&{auth}")
                print(f"Reproduciendo Playlist: {matched['name']}")
            else:
                print(f"No encontré la playlist '{query}'.")
                sys.exit(1)

        if args.aleatorio:
            random.shuffle(urls_to_play)

        subprocess.run(["killall", "-q", "mpv"])
        mpv_cmd = ["mpv", "--no-video"] + urls_to_play
        subprocess.Popen(mpv_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("Reproductor iniciado.")

    except Exception as e:
        print(f"Error al procesar la música: {e}")

if __name__ == "__main__":
    main()
