import requests
import subprocess
import argparse
import random
import sys
import os
import urllib.parse

# ==================================
# CONFIGURACIÓN DE NAVIDROME
# ==================================
NAVIDROME_URL = "http://TU_IP_NAVIDROME:4533"
USER = "TU_USUARIO"
TOKEN = "TU_TOKEN"
SALT = "TU_SALT"
CLIENT = "PuckAssistant"
TIMEOUT = 10

def get_auth():
    return f"u={USER}&t={TOKEN}&s={SALT}&v=1.16.1&c={CLIENT}&f=json"

def api(endpoint, extra=""):
    url = f"{NAVIDROME_URL}/rest/{endpoint}?{extra}&{get_auth()}"
    r = requests.get(url, timeout=TIMEOUT).json()["subsonic-response"]
    if r.get("status") != "ok":
        raise RuntimeError(r.get("error", {}).get("message", "respuesta inválida de Navidrome"))
    return r

def main():
    parser = argparse.ArgumentParser(description="Controlador de música para Puck")
    parser.add_argument("query", nargs="*", help="Búsqueda de canción, álbum o playlist")
    parser.add_argument("--tipo", choices=["cancion", "album", "playlist"], default="cancion")
    parser.add_argument("--aleatorio", action="store_true", help="Activar modo aleatorio")
    parser.add_argument("--accion", choices=["play", "pause", "stop", "toggle", "next", "previous", "volumen", "actual"], help="Acción multimedia")
    parser.add_argument("--valor", type=int, help="Valor para el volumen (0 a 100)")
    args = parser.parse_args()

    env = os.environ.copy()
    env["DISPLAY"] = ":0"
    env["WAYLAND_DISPLAY"] = "wayland-0"
    env["XDG_RUNTIME_DIR"] = f"/run/user/{os.getuid()}"

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
                            try:
                                subprocess.run(["wpctl", "set-volume", mpv_id, str(volumen_decimal)], check=True)
                                encontrado = True
                                break
                            except:
                                pass # Si wpctl tira error, lo ignora y pasa al plan B (pactl)

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

            elif args.accion == "actual":
                meta = subprocess.run(["playerctl", "--player=mpv", "metadata", "--format", "{{title}} - {{artist}} ({{album}})"],
                                      capture_output=True, text=True, env=env)
                estado = subprocess.run(["playerctl", "--player=mpv", "status"], capture_output=True, text=True, env=env)
                if meta.returncode == 0 and meta.stdout.strip():
                    print(f"Ahora suena ({estado.stdout.strip() or 'Playing'}): {meta.stdout.strip()}")
                else:
                    print("No hay música sonando ahora.")

            elif args.accion in ["pause", "stop"]:
                subprocess.run(["killall", "-q", "mpv"])
                print("Música detenida.")
            else:
                accion = "play-pause" if args.accion == "toggle" else args.accion
                subprocess.run(["playerctl", "--player=mpv", accion], env=env)
                print(f"Acción ejecutada: {args.accion}")
        except Exception as e:
            print(f"Error al procesar la acción: {e}")
        return

    if not args.query:
        print("No se especificó qué reproducir.")
        sys.exit(1)

    query = " ".join(args.query)
    q = urllib.parse.quote(query)
    urls_to_play = []

    def stream(song_id):
        return f"{NAVIDROME_URL}/rest/stream.view?id={song_id}&{get_auth()}"

    try:
        if args.tipo == "cancion":
            res = api("search3.view", f"query={q}&songCount=20")
            songs = res.get("searchResult3", {}).get("song", [])
            if not songs:
                print(f"No encontré ninguna canción para '{query}'.")
                sys.exit(1)

            # 1. Buscamos primero si hay una canción con el título EXACTO
            query_lower = query.lower()
            song = next((s for s in songs if s.get("title", "").lower() == query_lower), None)

            # 2. Si no hay exacta, buscamos una que contenga la palabra en el título
            if not song:
                song = next((s for s in songs if query_lower in s.get("title", "").lower()), songs[0])

            urls_to_play.append(stream(song["id"]))
            print(f"Reproduciendo: {song['title']} - {song['artist']}")

        elif args.tipo == "album":
            res = api("search3.view", f"query={q}&albumCount=1")
            albums = res.get("searchResult3", {}).get("album", [])
            if not albums:
                print(f"No encontré ningún álbum para '{query}'.")
                sys.exit(1)
            album_data = api("getAlbum.view", f"id={albums[0]['id']}")
            for song in album_data["album"]["song"]:
                urls_to_play.append(stream(song["id"]))
            print(f"Reproduciendo álbum: {albums[0].get('name', query)}")

        elif args.tipo == "playlist":
            res = api("getPlaylists.view")
            playlists = res["playlists"].get("playlist", [])
            matched = next((p for p in playlists if query.lower() in p["name"].lower()), None)
            if not matched:
                print(f"No encontré la playlist '{query}'.")
                sys.exit(1)
            pl_data = api("getPlaylist.view", f"id={matched['id']}")
            for song in pl_data["playlist"].get("entry", []):
                urls_to_play.append(stream(song["id"]))
            print(f"Reproduciendo playlist: {matched['name']}")

        if not urls_to_play:
            print("No hay canciones para reproducir.")
            sys.exit(1)

        if args.aleatorio:
            random.shuffle(urls_to_play)

        subprocess.run(["killall", "-q", "mpv"])
        mpv_cmd = ["mpv", "--no-video"] + urls_to_play
        subprocess.Popen(mpv_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("Reproductor iniciado.")

    except Exception as e:
        print(f"Error al procesar la música: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
