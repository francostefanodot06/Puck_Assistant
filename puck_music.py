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
