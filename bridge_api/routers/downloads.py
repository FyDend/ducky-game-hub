from fastapi import APIRouter, BackgroundTasks
import os
import requests
import urllib.parse
import shutil
import threading
import subprocess

router = APIRouter()

ACTIVE_DOWNLOADS = {}
ACTIVE_EXTRACTIONS = set()
EXTRACTION_LOCK = threading.Lock()

import re

def extract_with_progress(fpath: str, extract_to: str, progress_callback=None):
    process = subprocess.Popen(
        ["7z", "x", fpath, f"-o{extract_to}", "-y", "-bsp1"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    while True:
        line = process.stdout.readline()
        if not line and process.poll() is not None:
            break
        if line:
            match = re.search(r'(\d+)%', line)
            if match:
                percent = int(match.group(1))
                if progress_callback:
                    progress_callback(percent)
                    
    process.communicate()
    if process.returncode != 0:
        raise subprocess.CalledProcessError(process.returncode, process.args)

def background_download(url: str, console: str, expected_size: int = 0):
    try:
        parsed_link = urllib.parse.urlparse(url)
        name_param = urllib.parse.parse_qs(parsed_link.query).get('name', [''])[0]
        if name_param:
            filename = os.path.basename(name_param)
        else:
            filename = urllib.parse.unquote(url.split('/')[-1])
            
        folder_path = f"/roms/{console}"
        os.makedirs(folder_path, exist_ok=True)
        save_path = f"{folder_path}/{filename}"
        
        ACTIVE_DOWNLOADS[filename] = {"status": "Descargando", "progress": 0, "console": console, "url_original": url}
        
        if "minerva-archive.org" in url:
            from qbit_helper import download_via_qbittorrent
            
            def progress_cb(prog: int, status: str = "Descargando", torrent_hash: str = None,
                            dlspeed: int = 0, eta: int = -1):
                ACTIVE_DOWNLOADS[filename]["progress"] = prog
                ACTIVE_DOWNLOADS[filename]["status"] = status
                ACTIVE_DOWNLOADS[filename]["dlspeed"] = dlspeed
                ACTIVE_DOWNLOADS[filename]["eta"] = eta
                if torrent_hash:
                    ACTIVE_DOWNLOADS[filename]["torrent_hash"] = torrent_hash
                
            download_via_qbittorrent(filename, folder_path, progress_cb, full_path=name_param)
            
            ACTIVE_DOWNLOADS[filename]["status"] = "Completado"
            ACTIVE_DOWNLOADS[filename]["progress"] = 100
            print(f"¡Descarga torrent completada! Guardado en {folder_path}", flush=True)
        else:
            print(f"Descargando {filename} en {folder_path}...", flush=True)
            with requests.get(url, stream=True, timeout=60) as r:
                r.raise_for_status()
                total_size = int(r.headers.get('content-length', 0))
                if total_size == 0 and expected_size > 0:
                    total_size = expected_size
                downloaded = 0
                
                with open(save_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            ACTIVE_DOWNLOADS[filename]["progress"] = int((downloaded / total_size) * 100)
                        
            ACTIVE_DOWNLOADS[filename]["status"] = "Completado"
            ACTIVE_DOWNLOADS[filename]["progress"] = 100
            print(f"¡Descarga completada! Guardado en {save_path}", flush=True)
    except Exception as e:
        if filename in ACTIVE_DOWNLOADS:
            ACTIVE_DOWNLOADS[filename]["status"] = "Error"
        print(f"Error en descarga: {str(e)}", flush=True)

def sync_active_downloads_with_qbit():
    try:
        import qbittorrentapi
        qbt_client = qbittorrentapi.Client(host='qbittorrent:8080', REQUESTS_ARGS={'timeout': 30})
        qbt_client.auth_log_in()
        torrents = qbt_client.torrents_info()
        
        for t in torrents:
            if t.state_enum.is_complete:
                try:
                    files = qbt_client.torrents_files(torrent_hash=t.hash)
                    active_files = [f for f in files if f.priority > 0]
                    if not active_files:
                        active_files = files
                    target_file = max(active_files, key=lambda f: f.size) if active_files else None
                    if target_file:
                        console = "xbox"
                        if "/roms/" in t.save_path:
                            console = t.save_path.split("/roms/")[-1].strip("/")
                        
                        fpath = os.path.join(f"/roms/{console}", target_file.name)
                        if os.path.exists(fpath) and (fpath.endswith('.zip') or fpath.endswith('.7z')):
                            filename_base = os.path.basename(target_file.name)
                            with EXTRACTION_LOCK:
                                if filename_base in ACTIVE_EXTRACTIONS:
                                    continue
                                ACTIVE_EXTRACTIONS.add(filename_base)
                            
                            print(f"Auto-recuperación: Detectado torrent completo sin extraer ({filename_base}). Extrayendo en segundo plano...", flush=True)
                            
                            def extract_bg_sync(fp, c, h, name, tf):
                                try:
                                    ACTIVE_DOWNLOADS[name] = {
                                        "status": "Extrayendo",
                                        "progress": 0,
                                        "console": c,
                                        "torrent_hash": h
                                    }
                                    def cb(pct):
                                        ACTIVE_DOWNLOADS[name]["progress"] = pct
                                    extract_with_progress(fp, f"/roms/{c}", cb)
                                    qbt_client.torrents_delete(delete_files=True, torrent_hashes=h)
                                    parts = tf.name.split('/')
                                    if len(parts) > 1:
                                        top_dir = os.path.join(f"/roms/{c}", parts[0])
                                        if os.path.exists(top_dir):
                                            shutil.rmtree(top_dir)
                                    ACTIVE_DOWNLOADS[name]["status"] = "Completado"
                                    print(f"Auto-recuperación completada y limpia para: {name}", flush=True)
                                except Exception as ext_bg_ex:
                                    print(f"Error en extracción auto-recuperada de {name}: {ext_bg_ex}", flush=True)
                                    ACTIVE_DOWNLOADS[name]["status"] = "Error"
                                finally:
                                    with EXTRACTION_LOCK:
                                        ACTIVE_EXTRACTIONS.discard(name)
                                    
                            threading.Thread(target=extract_bg_sync, args=(fpath, console, t.hash, filename_base, target_file), daemon=True).start()
                except Exception as sync_loop_err:
                    print(f"Aviso: Error procesando torrent completo en inicio: {sync_loop_err}", flush=True)
                continue
                
            try:
                files = qbt_client.torrents_files(torrent_hash=t.hash)
            except Exception:
                continue
                
            active_files = [f for f in files if f.priority > 0]
            if len(active_files) > 5:
                continue
                
            target_file = next((f for f in active_files), None)
            if not target_file:
                filename = t.name
            else:
                filename = os.path.basename(target_file.name)
                
            console = "xbox"
            if "/roms/" in t.save_path:
                console = t.save_path.split("/roms/")[-1].strip("/")
                
            hash_already_registered = False
            for fn, info in ACTIVE_DOWNLOADS.items():
                if info.get("torrent_hash") == t.hash and fn != filename:
                    hash_already_registered = True
                    break
            if hash_already_registered:
                continue
 
            if filename not in ACTIVE_DOWNLOADS or ACTIVE_DOWNLOADS[filename]["status"] == "Error":
                if t.state == 'error':
                    ACTIVE_DOWNLOADS[filename] = {
                        "status": "Error",
                        "progress": int(t.progress * 100),
                        "console": console,
                        "torrent_hash": t.hash,
                        "detalle": "El torrent tiene un estado de error en qBittorrent (permisos/red)"
                    }
                    continue

                status = "Pausado" if "paused" in t.state.lower() else "Descargando"
                progress = int(t.progress * 100)
                ACTIVE_DOWNLOADS[filename] = {
                    "status": status,
                    "progress": progress,
                    "console": console,
                    "torrent_hash": t.hash,
                    "dlspeed": getattr(t, 'dlspeed', 0),
                    "eta": getattr(t, 'eta', -1),
                }
                
                def monitor_restored(fn, h, c):
                    print(f"Monitoreo restaurado iniciado para {fn}...", flush=True)
                    import time
                    qbt = qbittorrentapi.Client(host='qbittorrent:8080', REQUESTS_ARGS={'timeout': 30})
                    try:
                        qbt.auth_log_in()
                    except Exception as login_ex:
                        print(f"Aviso: Error inicial al conectar en monitoreo restaurado para {fn}: {login_ex}", flush=True)
                    
                    consecutive_errors = 0
                    while True:
                        try:
                            if fn not in ACTIVE_DOWNLOADS:
                                break
                            if ACTIVE_DOWNLOADS[fn]["status"] == "Completado" and ACTIVE_DOWNLOADS[fn]["progress"] >= 100:
                                break
                                
                            try:
                                t_info_list = qbt.torrents_info(torrent_hashes=h)
                                if not t_info_list:
                                    print(f"El torrent para {fn} ya no existe en qBittorrent.", flush=True)
                                    break
                                t_info = t_info_list[0]
                                consecutive_errors = 0
                            except Exception as api_ex:
                                err_str = str(api_ex).lower()
                                if "timeout" in err_str or "connection" in err_str or "max retries" in err_str or "readtimeout" in err_str:
                                    consecutive_errors += 1
                                    print(f"Aviso: Error temporal de conexión en monitoreo restaurado de {fn} (Intento {consecutive_errors}): {api_ex}", flush=True)
                                    if consecutive_errors > 15:
                                        raise api_ex
                                    time.sleep(5)
                                    continue
                                else:
                                    raise api_ex
                            
                            prog = int(t_info.progress * 100)
                            stat = "Pausado" if "paused" in t_info.state.lower() else "Descargando"

                            ACTIVE_DOWNLOADS[fn]["progress"] = prog
                            ACTIVE_DOWNLOADS[fn]["status"] = stat
                            ACTIVE_DOWNLOADS[fn]["dlspeed"] = getattr(t_info, 'dlspeed', 0)
                            ACTIVE_DOWNLOADS[fn]["eta"] = getattr(t_info, 'eta', -1)
                            
                            if t_info.state_enum.is_complete or prog >= 100:
                                ACTIVE_DOWNLOADS[fn]["status"] = "Extrayendo"
                                ACTIVE_DOWNLOADS[fn]["progress"] = 0
                                
                                fls = qbt.torrents_files(torrent_hash=h)
                                tgt = next((f for f in fls if f.priority > 0), None)
                                if tgt:
                                    fpath = os.path.join(f"/roms/{c}", tgt.name)
                                    if os.path.exists(fpath) and (fpath.endswith('.zip') or fpath.endswith('.7z')):
                                        print(f"Extrayendo descarga restaurada: {fpath}", flush=True)
                                        def cb(pct):
                                            ACTIVE_DOWNLOADS[fn]["progress"] = pct
                                        extract_with_progress(fpath, f"/roms/{c}", cb)
                                        
                                qbt.torrents_delete(delete_files=True, torrent_hashes=h)
                                if tgt:
                                    parts = tgt.name.split('/')
                                    if len(parts) > 1:
                                        top_dir = os.path.join(f"/roms/{c}", parts[0])
                                        if os.path.exists(top_dir):
                                            shutil.rmtree(top_dir)
                                            
                                ACTIVE_DOWNLOADS[fn]["status"] = "Completado"
                                print(f"Descarga restaurada completada: {fn}", flush=True)
                                break
                        except Exception as ex:
                            print(f"Error fatal en monitoreo restaurado de {fn}: {ex}", flush=True)
                            if fn in ACTIVE_DOWNLOADS:
                                ACTIVE_DOWNLOADS[fn]["status"] = "Error"
                            break
                        time.sleep(5)
                
                threading.Thread(target=monitor_restored, args=(filename, t.hash, console), daemon=True).start()
    except Exception as e:
        print(f"Error en sync_active_downloads_with_qbit: {e}", flush=True)

@router.get("/descargas")
def estado_descargas():
    sync_active_downloads_with_qbit()
    return ACTIVE_DOWNLOADS

@router.post("/descargas/pausar")
def pausar_descarga(filename: str):
    try:
        info = ACTIVE_DOWNLOADS.get(filename)
        if not info or "torrent_hash" not in info:
            return {"estado": "Error", "detalle": "Descarga no encontrada o sin hash de torrent"}
        
        import qbittorrentapi
        qbt_client = qbittorrentapi.Client(host='qbittorrent:8080')
        qbt_client.auth_log_in()
        qbt_client.torrents_pause(torrent_hashes=info["torrent_hash"])
        ACTIVE_DOWNLOADS[filename]["status"] = "Pausado"
        return {"estado": "OK", "mensaje": "Descarga pausada"}
    except Exception as e:
        return {"estado": "Error", "detalle": str(e)}

@router.post("/descargas/reanudar")
def reanudar_descarga(filename: str):
    try:
        info = ACTIVE_DOWNLOADS.get(filename)
        if not info or "torrent_hash" not in info:
            return {"estado": "Error", "detalle": "Descarga no encontrada o sin hash de torrent"}
        
        import qbittorrentapi
        qbt_client = qbittorrentapi.Client(host='qbittorrent:8080')
        qbt_client.auth_log_in()
        qbt_client.torrents_resume(torrent_hashes=info["torrent_hash"])
        ACTIVE_DOWNLOADS[filename]["status"] = "Descargando"
        return {"estado": "OK", "mensaje": "Descarga reanudada"}
    except Exception as e:
        return {"estado": "Error", "detalle": str(e)}

@router.post("/descargas/cancelar")
def cancelar_descarga(filename: str):
    try:
        info = ACTIVE_DOWNLOADS.get(filename)
        if not info:
            return {"estado": "Error", "detalle": "Descarga no encontrada"}
        
        torrent_hash = info.get("torrent_hash")
        if torrent_hash:
            import qbittorrentapi
            qbt_client = qbittorrentapi.Client(host='qbittorrent:8080')
            qbt_client.auth_log_in()
            qbt_client.torrents_delete(delete_files=True, torrent_hashes=torrent_hash)
        
        if filename in ACTIVE_DOWNLOADS:
            del ACTIVE_DOWNLOADS[filename]
        return {"estado": "OK", "mensaje": "Descarga cancelada y eliminada"}
    except Exception as e:
        return {"estado": "Error", "detalle": str(e)}

@router.post("/descargas/limpiar")
def limpiar_descarga(filename: str):
    try:
        info = ACTIVE_DOWNLOADS.get(filename)
        if not info:
            return {"estado": "Error", "detalle": "Descarga no encontrada"}
        
        status = info.get("status", "")
        if status not in ("Completado", "Error"):
            return {"estado": "Error", "detalle": f"Solo se pueden limpiar descargas completadas o con error (estado actual: {status})"}
        
        torrent_hash = info.get("torrent_hash")
        if torrent_hash and status == "Error":
            try:
                import qbittorrentapi
                qbt_client = qbittorrentapi.Client(host='qbittorrent:8080')
                qbt_client.auth_log_in()
                qbt_client.torrents_delete(delete_files=False, torrent_hashes=torrent_hash)
            except Exception:
                pass
        
        del ACTIVE_DOWNLOADS[filename]
        return {"estado": "OK", "mensaje": "Entrada limpiada correctamente"}
    except Exception as e:
        return {"estado": "Error", "detalle": str(e)}

@router.post("/descargas/reintentar")
def reintentar_descarga(filename: str, background_tasks: BackgroundTasks):
    try:
        info = ACTIVE_DOWNLOADS.get(filename)
        if not info:
            return {"estado": "Error", "detalle": "Descarga no encontrada"}
        
        status = info.get("status", "")
        if status != "Error":
            return {"estado": "Error", "detalle": f"Solo se pueden reintentar descargas con error (estado actual: {status})"}
        
        url_original = info.get("url_original", "")
        console = info.get("console", "snes")
        
        if not url_original:
            return {"estado": "Error", "detalle": "No se encontró la URL original para reintentar. Por favor, descarga el juego nuevamente desde el catálogo."}
        
        torrent_hash = info.get("torrent_hash")
        if torrent_hash:
            try:
                import qbittorrentapi
                qbt_client = qbittorrentapi.Client(host='qbittorrent:8080')
                qbt_client.auth_log_in()
                qbt_client.torrents_delete(delete_files=True, torrent_hashes=torrent_hash)
            except Exception:
                pass
        
        del ACTIVE_DOWNLOADS[filename]
        background_tasks.add_task(background_download, url_original, console, 0)
        return {"estado": "OK", "mensaje": "Reintentando descarga en segundo plano"}
    except Exception as e:
        return {"estado": "Error", "detalle": str(e)}

@router.get("/descargar")
def descargar_torrent(url_torrent: str, background_tasks: BackgroundTasks, console: str = "snes", expected_size: int = 0):
    background_tasks.add_task(background_download, url_torrent, console, expected_size)
    return {"estado": "OK", "mensaje": "Descarga iniciada en segundo plano"}

@router.delete("/borrar")
def borrar_juego(rom_path: str):
    try:
        if not rom_path.startswith("/roms/"):
            return {"estado": "Error", "detalle": "Ruta no permitida"}
        
        if os.path.exists(rom_path):
            if os.path.isdir(rom_path):
                shutil.rmtree(rom_path)
            else:
                os.remove(rom_path)
            return {"estado": "OK", "mensaje": "Juego borrado correctamente"}
        else:
            return {"estado": "Error", "detalle": "Archivo no encontrado"}
    except Exception as e:
        return {"estado": "Error Interno", "detalle": str(e)}
