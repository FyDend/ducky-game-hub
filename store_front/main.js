document.addEventListener('DOMContentLoaded', () => {
  const API_BASE_URL = (window.location.protocol === 'file:') ? 'http://127.0.0.1:8000' : `http://${window.location.hostname}:8000`;

  // --- Toast Notification System ---
  function showToast(message, type = 'info', duration = 3000) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    let icon = 'ℹ';
    if (type === 'success') icon = '';
    if (type === 'error') icon = '';
    if (type === 'warning') icon = '';

    toast.innerHTML = `
      <div class="toast-icon">${icon}</div>
      <div class="toast-message">${message}</div>
    `;

    container.appendChild(toast);

    toast.offsetHeight; // trigger reflow
    toast.classList.add('show');

    setTimeout(() => {
      toast.classList.remove('show');
      toast.addEventListener('transitionend', () => {
        toast.remove();
      });
    }, duration);
  }

  // Override window.alert to use our toasts
  window.alert = (msg) => showToast(msg, 'warning', 4000);

  // Expose to window for easy access
  window.showToast = showToast;

  // --- Connection Status Monitor ---
  let isApiOnline = true;

  function checkConnection() {
    fetch(`${API_BASE_URL}/health`)
      .then(res => res.json())
      .then(data => {
        if (data.estado === 'OK') {
          if (!isApiOnline) {
            isApiOnline = true;
            updateConnectionUI(true);
            showToast("Conexión con el servidor restablecida.", "success");
          }
        } else {
          handleOffline();
        }
      })
      .catch(err => {
        handleOffline();
      });
  }

  function handleOffline() {
    if (isApiOnline) {
      isApiOnline = false;
      updateConnectionUI(false);
      showToast("Se perdió la conexión con el servidor.", "error");
    }
  }

  function updateConnectionUI(online) {
    const badge = document.getElementById('connection-badge');
    const overlay = document.getElementById('offline-overlay');
    const offlineUrl = document.getElementById('offline-url');

    if (badge) {
      if (online) {
        badge.className = 'connection-badge online';
        badge.querySelector('.dot').style.background = '#4cd137';
        badge.querySelector('.text').textContent = 'API ONLINE';
      } else {
        badge.className = 'connection-badge offline';
        badge.querySelector('.dot').style.background = '#e84118';
        badge.querySelector('.text').textContent = 'API OFFLINE';
      }
    }

    if (overlay) {
      if (online) {
        overlay.classList.add('hidden');
      } else {
        if (offlineUrl) {
          offlineUrl.textContent = API_BASE_URL;
        }
        overlay.classList.remove('hidden');
      }
    }
  }

  // Iniciar monitoreo de conexión cada 15 segundos
  setInterval(checkConnection, 15000);
  checkConnection();

  // --- Último Jugado System ---
  function renderLastPlayed() {
    const container = document.getElementById('last-played-container');
    const lastPlayedData = localStorage.getItem('retro_last_played');
    
    // Only show last played banner when we are in Catalog Mode or Local Mode, and no active search text, and on page 1
    if (!lastPlayedData || (searchInput.value && searchInput.value.trim() !== "") || currentPage > 1 || (!isCatalogMode && navFavorites.classList.contains('active')) || navSettings.classList.contains('active') || navDownloads.classList.contains('active')) {
      if (container) container.classList.add('hidden');
      return;
    }
    
    const lastPlayed = JSON.parse(lastPlayedData);
    const imgEl = document.getElementById('last-played-img');
    const titleEl = document.getElementById('last-played-title');
    const consoleEl = document.getElementById('last-played-console');
    const timeEl = document.getElementById('last-played-time');
    const playBtnEl = document.getElementById('last-played-play-btn');
    
    if (imgEl) imgEl.src = lastPlayed.image || 'https://placehold.co/200x250/2f3640/fbc531?text=NO+COVER';
    if (titleEl) titleEl.textContent = lastPlayed.title;
    if (consoleEl) {
      consoleEl.textContent = lastPlayed.console.toUpperCase();
      // Set coloring by console
      let bgColor = '#6f1e51';
      if (lastPlayed.console === 'snes') bgColor = '#5d28b1';
      else if (lastPlayed.console === 'n64') bgColor = '#e00000';
      else if (lastPlayed.console === 'nes') bgColor = '#7f8fa6';
      else if (lastPlayed.console === 'gb') bgColor = '#27ae60';
      else if (lastPlayed.console === 'gba') bgColor = '#d35400';
      else if (lastPlayed.console === 'nds') bgColor = '#2980b9';
      else if (lastPlayed.console === 'xbox') bgColor = '#10ac84';
      consoleEl.style.background = bgColor;
    }
    
    if (timeEl) {
      const minutesAgo = Math.max(0, Math.floor((Date.now() - lastPlayed.timestamp) / 60000));
      if (minutesAgo < 1) {
        timeEl.textContent = "Jugado hace un instante";
      } else if (minutesAgo < 60) {
        timeEl.textContent = `Jugado hace ${minutesAgo} min`;
      } else {
        const hoursAgo = Math.floor(minutesAgo / 60);
        if (hoursAgo < 24) {
          timeEl.textContent = `Jugado hace ${hoursAgo} ${hoursAgo === 1 ? 'hora' : 'horas'}`;
        } else {
          timeEl.textContent = `Jugado hace ${Math.floor(hoursAgo / 24)} días`;
        }
      }
    }
    
    if (playBtnEl) {
      playBtnEl.onclick = (e) => {
        e.stopPropagation();
        const originalText = playBtnEl.textContent;
        playBtnEl.textContent = 'INIT...';
        playBtnEl.disabled = true;
        
        isGamePlaying = true;
        stopGamepadPolling();
        
        const apiUrl = `${API_BASE_URL}/jugar?core=${encodeURIComponent(lastPlayed.core)}&rom_path=${encodeURIComponent(lastPlayed.path)}&console=${encodeURIComponent(lastPlayed.console)}`;
        fetch(apiUrl)
          .then(res => res.json())
          .then(data => {
            if (data.estado === 'OK') {
              lastPlayed.timestamp = Date.now();
              localStorage.setItem('retro_last_played', JSON.stringify(lastPlayed));
              renderLastPlayed();
              showToast(`Iniciando ${lastPlayed.title}...`, 'success');
              
              setTimeout(() => {
                  let checkGameInterval = setInterval(() => {
                      fetch(`${API_BASE_URL}/estado_emulador`)
                        .then(res => res.json())
                        .then(dataCheck => {
                            if (!dataCheck.activo) {
                                clearInterval(checkGameInterval);
                                isGamePlaying = false;
                                startGamepadPolling();
                                playBtnEl.textContent = originalText;
                                playBtnEl.disabled = false;
                                fetch(`${API_BASE_URL}/foco`).catch(err => console.error("Error enfocando browser:", err));
                                setTimeout(() => {
                                    renderLastPlayed();
                                }, 500);
                            }
                        }).catch(err => {
                            console.error("Error comprobando estado del emulador:", err);
                        });
                  }, 2000);
              }, 8000);
            } else {
              isGamePlaying = false;
              startGamepadPolling();
              showToast("Error al iniciar juego: " + data.detalle, "error");
              playBtnEl.textContent = originalText;
              playBtnEl.disabled = false;
            }
          }).catch(err => {
            isGamePlaying = false;
            startGamepadPolling();
            showToast("Error de red al iniciar juego", "error");
            playBtnEl.textContent = originalText;
            playBtnEl.disabled = false;
          });
      };
    }
    
    if (container) container.classList.remove('hidden');
  }


  // DOM Elements
  const dynamicGrid = document.getElementById('dynamic-grid');
  const viewTitle = document.getElementById('view-title');
  const backBtn = document.getElementById('back-btn');
  const refreshLibraryBtn = document.getElementById('refresh-library-btn');
  
  const navCatalog = document.getElementById('nav-catalog');
  const navLocal = document.getElementById('nav-local');
  const navFavorites = document.getElementById('nav-favorites');
  const navDownloads = document.getElementById('nav-downloads');
  const navSettings = document.getElementById('nav-settings');
  const steamBtn = document.getElementById('nav-steam');
  const navButtons = [navCatalog, navLocal, navFavorites, navDownloads, navSettings, steamBtn];
  
  const searchInput = document.getElementById('search-input');
  const consoleFilter = document.getElementById('console-filter');
  const sortFilter = document.getElementById('sort-filter');
  const downloadsView = document.getElementById('downloads-view');
  const settingsView = document.getElementById('settings-view');
  const audioSelect = document.getElementById('audio-select');
  const gamepadTesterDisplay = document.getElementById('gamepad-tester-display');
  const navTv = document.getElementById('nav-tv');

  // Modal Elements
  const modal = document.getElementById('game-modal');
  const modalOverlay = document.getElementById('modal-overlay');
  const modalImg = document.getElementById('modal-img');
  const modalTitle = document.getElementById('modal-title');
  const modalYear = document.getElementById('modal-year');
  const modalStatus = document.getElementById('modal-status');
  
  const favBtn = document.getElementById('fav-btn');
  const versionContainer = document.getElementById('version-container');
  const versionSelect = document.getElementById('version-select');
  
  const playBtn = document.getElementById('play-btn');
  const downloadBtn = document.getElementById('download-btn');
  const deleteBtn = document.getElementById('delete-btn');

  let localGames = [];
  let catalogGames = [];
  let favorites = JSON.parse(localStorage.getItem('retro_favorites')) || [];
  let currentGame = null;
  let isCatalogMode = false;
  let downloadInterval = null;
  
  // State variables for Couch Mode and Gamepad navigation
  let focusedElement = null;
  let gamepadInterval = null;
  let lastButtonStates = {};
  let isKeyboardActive = false;
  let activeInputEl = null;
  let isGamePlaying = false;
  let isGamePaused = false;
  let isConfirmOpen = false;
  let isSelectorOpen = false;
  let activeSelectorEl = null;
  let isExplorerOpen = false;
  let activeExplorerTargetInput = null;
  let explorerCurrentPath = "";

  // Custom modal DOM nodes
  const confirmModal = document.getElementById('confirm-modal');
  const confirmTitle = document.getElementById('confirm-title');
  const confirmYesBtn = document.getElementById('confirm-yes-btn');
  const confirmNoBtn = document.getElementById('confirm-no-btn');

  const selectorModal = document.getElementById('selector-modal');
  const selectorTitle = document.getElementById('selector-title');
  const selectorOptionsGrid = document.getElementById('selector-options-grid');
  const selectorCloseBtn = document.getElementById('selector-close-btn');

  // --- WebSocket de Control Remoto para Joystick sin Foco ---
  let socket = null;
  let activeSettings = {
      video: { crt_shader: true, bilinear_filtering: true, aspect_ratio: "16:9", show_fps: true },
      versatility: { target_workspace: "1", target_monitor: "DP-1", host_monitor: "DP-1" },
      audio: { selected_sink: "" },
      controls: {
          profile: "keyboard",
          gamepad: {
              a: "b0", b: "b1", x: "b2", y: "b3",
              leftshoulder: "b4", rightshoulder: "b5", lefttrigger: "b6", righttrigger: "b7",
              back: "b10", start: "b11", guide: "b12",
              leftstick: "b8", rightstick: "b9",
              dpup: "h0.1", dpdown: "h0.4", dpleft: "h0.8", dpright: "h0.2"
          },
          gamepad2: {
              a: "b0", b: "b1", x: "b2", y: "b3",
              leftshoulder: "b4", rightshoulder: "b5", lefttrigger: "b6", righttrigger: "b7",
              back: "b10", start: "b11", guide: "b12",
              leftstick: "b8", rightstick: "b9",
              dpup: "h0.1", dpdown: "h0.4", dpleft: "h0.8", dpright: "h0.2"
          },
          keyboard: {
              up: "up", down: "down", left: "left", right: "right",
              a: "x", b: "z", x: "s", y: "a",
              l1: "q", r1: "w", l2: "e", r2: "r",
              select: "shift", start: "enter", guide: "escape"
          }
      },
      emulators: {
          ps1: "retroarch", ps2: "pcsx2", gamecube: "dolphin", wii: "dolphin", xbox: "xemu", psp: "ppsspp", default: "retroarch"
      }
  };
  let currentMappingAction = null;

  const CONTROL_DISPLAY_NAMES = {
      // Gamepad profile simplified displays (no "crucetas" / uses "D-PAD")
      "gamepad_dpup": "D-PAD ARRIBA",
      "gamepad_dpdown": "D-PAD ABAJO",
      "gamepad_dpleft": "D-PAD IZQUIERDA",
      "gamepad_dpright": "D-PAD DERECHA",
      "gamepad_a": "BOTON A",
      "gamepad_b": "BOTON B",
      "gamepad_x": "BOTON X",
      "gamepad_y": "BOTON Y",
      "gamepad_leftshoulder": "BUMPER LB",
      "gamepad_rightshoulder": "BUMPER RB",
      "gamepad_lefttrigger": "GATILLO LT",
      "gamepad_righttrigger": "GATILLO RT",
      "gamepad_back": "BOTON BACK",
      "gamepad_start": "BOTON START",
      "gamepad_guide": "BOTON GUIDE",
      "gamepad_leftstick": "BOTON L3 (STICK IZQ)",
      "gamepad_rightstick": "BOTON R3 (STICK DER)",

      // Keyboard profile simplified displays (no "crucetas" / direct names)
      "keyboard_up": "ARRIBA",
      "keyboard_down": "ABAJO",
      "keyboard_left": "IZQUIERDA",
      "keyboard_right": "DERECHA",
      "keyboard_a": "BOTON A",
      "keyboard_b": "BOTON B",
      "keyboard_x": "BOTON X",
      "keyboard_y": "BOTON Y",
      "keyboard_l1": "BUMPER LB",
      "keyboard_r1": "BUMPER RB",
      "keyboard_l2": "GATILLO LT",
      "keyboard_r2": "GATILLO RT",
      "keyboard_select": "BOTON BACK",
      "keyboard_start": "BOTON START",
      "keyboard_guide": "BOTON GUIDE"
  };

  function connectWebSocket() {
      const wsUrl = (window.location.protocol === 'file:') ? 'ws://127.0.0.1:8000/ws_events' : `ws://${window.location.hostname}:8000/ws_events`;
      socket = new WebSocket(wsUrl);

      socket.onopen = () => {
          console.log("[WebSocket] Conectado para control remoto de joystick sin foco.");
      };

      socket.onmessage = (event) => {
          try {
              const data = JSON.parse(event.data);
              
              // Si recibimos un reporte de input en bruto
              if (data.action === "raw_event" && data.raw) {
                  const testerDisplay = document.getElementById('gamepad-tester-display');
                  if (testerDisplay) {
                      if (data.raw.type === "button") {
                          testerDisplay.textContent = `MANDO: BOTON ${data.raw.number} -> ${data.raw.value === 1 ? 'PRESIONADO' : 'LIBERADO'}`;
                      } else if (data.raw.type === "axis") {
                          testerDisplay.textContent = `MANDO: EJE ${data.raw.number} -> VAL: ${data.raw.value}`;
                      }
                      testerDisplay.style.color = 'var(--accent-gold)';
                  }
                  
                  // Actualizar también el tester del asistente (wizard) si está abierto
                  const wizardKeyDetector = document.getElementById('wizard-key-detected');
                  const wizardEl = document.getElementById('setup-wizard');
                  const isWizardOpen = wizardEl && !wizardEl.classList.contains('hidden');
                  if (wizardKeyDetector && isWizardOpen) {
                      if (data.raw.type === "button") {
                          wizardKeyDetector.textContent = `MANDO: BOTON ${data.raw.number} (${data.raw.value === 1 ? 'PULSADO' : 'LIBERADO'})`;
                          wizardKeyDetector.style.color = 'var(--accent-gold)';
                      } else if (data.raw.type === "axis" && Math.abs(data.raw.value) > 16000) {
                          wizardKeyDetector.textContent = `MANDO: EJE ${data.raw.number} (VALOR: ${data.raw.value})`;
                          wizardKeyDetector.style.color = 'var(--accent-gold)';
                      }
                      const gamepadDeviceInfo = document.getElementById('wizard-gamepad-device-info');
                      if (gamepadDeviceInfo) {
                          gamepadDeviceInfo.textContent = "Mando detectado y activo (Daemon WebSocket).";
                          gamepadDeviceInfo.style.color = 'var(--accent-cyan)';
                      }
                  }
                  
                  const profileSelect = document.getElementById('cfg-profile');
                  const profileVal = profileSelect ? profileSelect.value : 'gamepad';
                  if (currentMappingAction && profileVal.startsWith('gamepad')) {
                      if (data.raw.type === "button" && data.raw.value === 1) {
                          activeSettings.controls[profileVal][currentMappingAction] = `b${data.raw.number}`;
                          currentMappingAction = null;
                          renderMappingGrid();
                      } else if (data.raw.type === "axis" && Math.abs(data.raw.value) > 16000) {
                          activeSettings.controls[profileVal][currentMappingAction] = `a${data.raw.number}`;
                          currentMappingAction = null;
                          renderMappingGrid();
                      }
                  }
                  return;
              }
              
              if (data.action) {
                  console.log("[WebSocket] Recibido evento remoto:", data.action);
                  // El evento de toggle_pause fue eliminado, ignorarlo
                  handleRemoteInput(data.action);
              }
          } catch (e) {
              console.error("[WebSocket] Error parseando datos:", e);
          }
      };

      socket.onclose = () => {
          console.log("[WebSocket] Desconectado. Reintentando en 3 segundos...");
          setTimeout(connectWebSocket, 3000);
      };

      socket.onerror = (err) => {
          console.error("[WebSocket] Error:", err);
          socket.close();
      };
  }

  function handleRemoteInput(action) {
      if (isGamePlaying) {
          console.log("[WebSocket] Evento ignorado porque un juego está ejecutándose.");
          return;
      }
      
      const isCouchActive = document.body.classList.contains('couch-mode');
      if (!isCouchActive) return;

      // SI ESTAMOS MAPEANDO CONTROLES, IGNORAR LA NAVEGACION POR COMPLETO PARA EVITAR CONFLICTOS CON LOS BOTONES DE MAPEO
      if (currentMappingAction) {
          console.log("[WebSocket] Evento de navegación remota ignorado por estar remapeando controles.");
          return;
      }

      tryFullscreen(); // Asegurar pantalla completa al navegar remotamente

      if (action === 'up') {
          navigateSpatial('ArrowUp');
      } else if (action === 'down') {
          navigateSpatial('ArrowDown');
      } else if (action === 'left') {
          navigateSpatial('ArrowLeft');
      } else if (action === 'right') {
          navigateSpatial('ArrowRight');
      } else if (action === 'select') {
          if (focusedElement) {
              if (focusedElement === searchInput) {
                  showVirtualKeyboard();
                  return;
              }
              // Si el elemento es un select, llamar directamente a showCustomSelector en Couch Mode
              if (focusedElement.tagName === 'SELECT') {
                  const item = couchSelects.find(x => x.id === focusedElement.id);
                  const title = item ? item.title : 'SELECCIONAR';
                  showCustomSelector(focusedElement, title);
              } else {
                  focusedElement.click();
              }
              // Auto-focus el primer botón disponible del modal si se abrió uno
              setTimeout(() => {
                  if (!modal.classList.contains('hidden')) {
                      const firstModalBtn = modal.querySelector('.btn-primary:not(.hidden), .btn-secondary:not(.hidden)');
                      if (firstModalBtn) focusElement(firstModalBtn);
                  }
              }, 180);
          }
      } else if (action === 'cancel') {
          if (isExplorerOpen) {
              closeFolderExplorer();
              return;
          }
          if (isKeyboardActive) {
              hideVirtualKeyboard();
              return;
          }
          if (isSelectorOpen) {
              hideCustomSelector();
              return;
          }
          if (isConfirmOpen) {
              closeConfirmModal(false);
              return;
          }
          // Cerrar modal de mapeo de controles si está abierto
          const mappingModalEl = document.getElementById('controls-mapping-modal');
          if (mappingModalEl && !mappingModalEl.classList.contains('hidden')) {
              mappingModalEl.classList.add('hidden');
              const openMappingBtnRef = document.getElementById('open-mapping-btn');
              if (openMappingBtnRef) focusElement(openMappingBtnRef);
              return;
          }
          if (!modal.classList.contains('hidden')) {
              closeModal();
              setTimeout(() => {
                  const firstCard = document.querySelector('.game-card');
                  if (firstCard) focusElement(firstCard);
              }, 180);
          }
      }
  }

  connectWebSocket();

  // --- Helpers de formato para descargas ---
  function formatSpeed(bytesPerSec) {
    if (!bytesPerSec || bytesPerSec <= 0) return null;
    if (bytesPerSec >= 1024 * 1024) return `${(bytesPerSec / 1024 / 1024).toFixed(1)} MB/s`;
    if (bytesPerSec >= 1024)        return `${(bytesPerSec / 1024).toFixed(1)} KB/s`;
    return `${bytesPerSec} B/s`;
  }

  function formatETA(seconds) {
    if (seconds == null || seconds < 0 || seconds >= 8640000) return null;  // desconocido o ∞
    if (seconds < 60)    return `${seconds}s`;
    if (seconds < 3600)  return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
    return `${Math.floor(seconds / 86400)}d ${Math.floor((seconds % 86400) / 3600)}h`;
  }

  // --- Inicialización ---
  function loadData(initialLoad = false) {
    // Cargar Catálogo IA
    fetch(`${API_BASE_URL}/catalogo`)
      .then(res => res.json())
      .then(data => {
        if(data.estado === "OK") catalogGames = data.resultados;
        if(initialLoad) showCatalogView();
        else if (isCatalogMode) applyFilters();
      });

    // Cargar Librería Local
    fetch(`${API_BASE_URL}/libreria`)
      .then(res => res.json())
      .then(data => {
        localGames = data;
        if (!initialLoad && !isCatalogMode && !navDownloads.classList.contains('active')) {
            applyFilters();
        }
      });
  }

  // --- Pantalla Completa y Modo TV (Couch Mode) ---
  function tryFullscreen() {
      if (isGamePlaying) return;
      if (!document.fullscreenElement) {
          document.documentElement.requestFullscreen().catch(err => {
              console.log("Intento de pantalla completa bloqueado/no permitido por el navegador:", err);
          });
      }
  }

  // Solicitar pantalla completa ante cualquier interacción de usuario
  document.addEventListener('click', tryFullscreen);
  document.addEventListener('keydown', tryFullscreen);

  function setCouchMode(enabled, forceFocus = false) {
      if (enabled) {
          document.body.classList.add('couch-mode');
          if (navTv) {
              navTv.classList.add('active');
              navTv.textContent = ' MODO TELE: ON';
          }
          if (forceFocus || !focusedElement) {
              setTimeout(() => {
                  const first = document.querySelector('.game-card, .nav-btn');
                  if (first) focusElement(first);
              }, 300);
          }
          startGamepadPolling();
      } else {
          document.body.classList.remove('couch-mode');
          if (navTv) {
              navTv.classList.remove('active');
              navTv.textContent = ' MODO TELE: OFF';
          }
          if (focusedElement) {
              focusedElement.classList.remove('focused');
              focusedElement = null;
          }
          stopGamepadPolling();
      }
  }

  // --- Splash Screen & Startup Handler ---
  const splashScreen = document.getElementById('splash-screen');
  
  // Fetch settings on startup to check for first_run
  let startupSettingsPromise = fetch(`${API_BASE_URL}/ajustes`)
      .then(res => res.json())
      .then(settings => {
          activeSettings = settings;
          if (activeSettings && activeSettings.controls) {
              activeSettings.controls.player1_profile = activeSettings.controls.player1_profile || "gamepad";
              activeSettings.controls.player2_profile = activeSettings.controls.player2_profile || "gamepad2";
              activeSettings.controls.player3_profile = activeSettings.controls.player3_profile || "gamepad3";
              activeSettings.controls.player4_profile = activeSettings.controls.player4_profile || "gamepad4";

              if (!activeSettings.controls.gamepad2) {
                  activeSettings.controls.gamepad2 = Object.assign({}, activeSettings.controls.gamepad || {});
              }
              if (!activeSettings.controls.gamepad3) {
                  activeSettings.controls.gamepad3 = Object.assign({}, activeSettings.controls.gamepad || {});
              }
              if (!activeSettings.controls.gamepad4) {
                  activeSettings.controls.gamepad4 = Object.assign({}, activeSettings.controls.gamepad || {});
              }
          }
          
          // Popular tema
          const themeSelector = document.getElementById('cfg-theme');
          if (themeSelector) {
              const currentTheme = settings.theme || localStorage.getItem('retro_theme') || 'neon';
              themeSelector.value = currentTheme;
              document.body.setAttribute('data-theme', currentTheme);
              localStorage.setItem('retro_theme', currentTheme);
          }
          
          // Popular emuladores standalone
          const emus = settings.emulators || {};
          if (document.getElementById('emu-ps1')) document.getElementById('emu-ps1').value = emus.ps1 || 'retroarch';
          if (document.getElementById('emu-ps2')) document.getElementById('emu-ps2').value = emus.ps2 || 'pcsx2';
          if (document.getElementById('emu-gamecube')) document.getElementById('emu-gamecube').value = emus.gamecube || 'dolphin';
          if (document.getElementById('emu-wii')) document.getElementById('emu-wii').value = emus.wii || 'dolphin';
          if (document.getElementById('emu-xbox')) document.getElementById('emu-xbox').value = emus.xbox || 'xemu';
          if (document.getElementById('emu-psp')) document.getElementById('emu-psp').value = emus.psp || 'ppsspp';

          // Popular Video
          if (document.getElementById('cfg-crt')) document.getElementById('cfg-crt').checked = settings.video.crt_shader;
          if (document.getElementById('cfg-bilinear')) document.getElementById('cfg-bilinear').checked = settings.video.bilinear_filtering;
          if (document.getElementById('cfg-fps')) document.getElementById('cfg-fps').checked = settings.video.show_fps;
          if (document.getElementById('cfg-aspect')) document.getElementById('cfg-aspect').value = settings.video.aspect_ratio;
          
          // Popular Versatilidad - cargar screen_mode guardado directamente
          const savedMode = settings.screen_mode || 'single';
          
          // Setear la variable global ANTES de llamar la funcion
          window._settingsScreenMode = savedMode;
          
          if (typeof window.setSettingsScreenMode === 'function') {
              window.setSettingsScreenMode(savedMode);
          }
          
          if (document.getElementById('cfg-workspace-dual')) document.getElementById('cfg-workspace-dual').value = settings.versatility.target_workspace;
          if (document.getElementById('cfg-target-monitor-dual')) document.getElementById('cfg-target-monitor-dual').value = settings.versatility.target_monitor;
          if (document.getElementById('cfg-host-monitor-dual')) document.getElementById('cfg-host-monitor-dual').value = settings.versatility.host_monitor;
          if (document.getElementById('cfg-host-monitor-single')) document.getElementById('cfg-host-monitor-single').value = settings.versatility.host_monitor;
          if (document.getElementById('cfg-host-monitor-stream')) document.getElementById('cfg-host-monitor-stream').value = settings.versatility.host_monitor;
          if (document.getElementById('cfg-workspace-stream')) document.getElementById('cfg-workspace-stream').value = settings.versatility.target_workspace;
          
          // Sincronizar inputs ocultos por retrocompatibilidad
          if (document.getElementById('cfg-workspace')) document.getElementById('cfg-workspace').value = settings.versatility.target_workspace;
          if (document.getElementById('cfg-target-monitor')) document.getElementById('cfg-target-monitor').value = settings.versatility.target_monitor;
          if (document.getElementById('cfg-host-monitor')) document.getElementById('cfg-host-monitor').value = settings.versatility.host_monitor;

          // Popular Mapeo Perfil
          populateProfilesSelect(settings.controls.profile);
          
          // Renderizar grilla de mapeos
          renderMappingGrid();
          
          return settings;
      })
      .catch(err => {
          console.error("Error fetching settings on startup:", err);
          return null;
      });

  // Wait 3 seconds for premium splash screen animation, then fade out
  setTimeout(() => {
      if (splashScreen) {
          splashScreen.style.opacity = '0';
          splashScreen.addEventListener('transitionend', () => {
              splashScreen.style.display = 'none';
              
              // After splash fades out, check if first_run is active
              startupSettingsPromise.then(settings => {
                  if (settings && settings.first_run) {
                      startSetupWizard();
                  } else {
                      setCouchMode(true, true);
                  }
              });
          });
      } else {
          startupSettingsPromise.then(settings => {
              if (settings && settings.first_run) {
                  startSetupWizard();
              } else {
                  setCouchMode(true, true);
              }
          });
      }
  }, 3000);

  // Inicializar Modo Tele por defecto al arrancar (sin enfocar aún hasta que pase el splash)
  setCouchMode(true, false);

  loadData(true);

  // --- Navegación ---
  function updateNav(activeBtn) {
    navButtons.forEach(btn => btn.classList.remove('active'));
    if(activeBtn) activeBtn.classList.add('active');
    
    // Ocultar vistas especiales
    downloadsView.classList.add('hidden');
    settingsView.classList.add('hidden');
    dynamicGrid.classList.remove('hidden');
    const lastPlayedContainer = document.getElementById('last-played-container');
    if (lastPlayedContainer && (activeBtn === navDownloads || activeBtn === navSettings)) {
      lastPlayedContainer.classList.add('hidden');
    }
    
    let paginationContainer = document.getElementById('pagination-controls');
    if (paginationContainer) {
        if (activeBtn === navDownloads || activeBtn === navSettings) {
            paginationContainer.classList.add('hidden');
        } else {
            paginationContainer.classList.remove('hidden');
        }
    }
    
    if (downloadInterval) {
        clearInterval(downloadInterval);
        downloadInterval = null;
    }
  }

  // --- Definir controlador global de descargas ---
  window.controlDownload = function(filename, action) {
      const executeAction = () => {
          const url = `${API_BASE_URL}/descargas/${action}?filename=${encodeURIComponent(filename)}`;
          fetch(url, { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                if (data.estado !== 'OK') {
                    console.error('Error in controlDownload: ' + (data.detalle || 'Error desconocido'));
                }
                fetchDownloads();
            }).catch(err => {
                console.error("Error controlling download:", err);
            });
      };

      if (action === 'cancelar') {
          showConfirmModal(`¿CANCELAR Y ELIMINAR LA DESCARGA DE ${filename.toUpperCase()}?`, () => {
              executeAction();
          }, () => {
              // Cancelado, devolver foco al botón si es necesario
          });
      } else {
          executeAction();
      }
  };

  function showDownloadsView() {
    updateNav(navDownloads);
    viewTitle.textContent = "DESCARGAS ACTIVAS";
    dynamicGrid.classList.add('hidden');
    downloadsView.classList.remove('hidden');
    if (refreshLibraryBtn) refreshLibraryBtn.classList.add('hidden');
    
    window.fetchDownloads = function fetchDownloads() {
      let focusedFile = null;
      let focusedAction = null;
      if (focusedElement && downloadsView.contains(focusedElement)) {
          focusedFile = focusedElement.getAttribute('data-file');
          focusedAction = focusedElement.getAttribute('data-action');
      }
      fetch(`${API_BASE_URL}/descargas`)
        .then(res => res.json())
        .then(data => {
            let html = '';
            const files = Object.keys(data);
            if (files.length === 0) {
                downloadsView.innerHTML = `
                  <div style="text-align:center; padding: 60px 20px; color: #a0a0a0;">
                    <div style="font-size: 3rem; margin-bottom: 16px;"></div>
                    <p style="font-family: 'Press Start 2P', cursive; font-size: 0.7rem; line-height: 1.8;">
                      No hay descargas activas
                    </p>
                  </div>`;
                return;
            }
            
            files.forEach(filename => {
                const d = data[filename];
                const isComplete = d.status === 'Completado';
                const isError = d.status === 'Error';
                const isPaused = d.status === 'Pausado';
                const isExtracting = d.status === 'Extrayendo';
                const isActive = !isComplete && !isError;

                // Color scheme per state
                const barColor = isComplete ? '#4cd137' : isError ? '#e84118' : isPaused ? '#fbc531' : isExtracting ? '#9b59b6' : '#3498db';
                const borderColor = isComplete ? '#4cd137' : isError ? '#e84118' : isPaused ? '#fbc531' : isExtracting ? '#9b59b6' : '#3498db33';
                const bgColor = isComplete ? '#1a2e1a' : isError ? '#2e1a1a' : isExtracting ? '#281a30' : '#2f3640';
                
                const statusIcon = isComplete ? '' : isError ? '' : isPaused ? '' : isExtracting ? '' : '⬇';
                const statusLabel = isComplete ? 'COMPLETADO' : isError ? 'ERROR' : isPaused ? 'PAUSADO' : isExtracting ? 'EXTRAYENDO...' : 'DESCARGANDO';
                
                // Console badge
                const consoleBadge = d.console ? `<span style="background:#ffffff15; color:#aaa; font-size:0.5rem; font-family:'Press Start 2P',cursive; padding: 2px 6px; border-radius: 3px; margin-left: 8px;">${d.console.toUpperCase()}</span>` : '';

                // Progress bar with animation for active downloads
                const progressAnimation = (!isComplete && !isError && !isPaused) 
                    ? 'background-image: linear-gradient(90deg, rgba(255,255,255,0.1) 25%, transparent 25%, transparent 50%, rgba(255,255,255,0.1) 50%, rgba(255,255,255,0.1) 75%, transparent 75%); background-size: 20px 20px; animation: progress-stripe 1s linear infinite;'
                    : '';

                const safeFilename = filename.replace(/'/g, "\\'");

                // Action buttons
                let actionButtons = '';
                
                if (isActive) {
                    actionButtons = `
                    <div style="display: flex; gap: 8px; margin-top: 14px; justify-content: flex-end; flex-wrap: wrap;">
                        <button data-file="${safeFilename}" data-action="${isPaused ? 'reanudar' : 'pausar'}" onclick="controlDownload('${safeFilename}', '${isPaused ? 'reanudar' : 'pausar'}')"
                            style="padding: 6px 14px; font-size: 0.55rem; font-family: 'Press Start 2P', cursive;
                                   background: ${isPaused ? '#4cd137' : '#fbc531'}; color: #000; border: 2px solid #fff;
                                   box-shadow: 2px 2px 0px #000; cursor: pointer;">
                            ${isPaused ? '▶ REANUDAR' : ' PAUSAR'}
                        </button>
                        <button data-file="${safeFilename}" data-action="cancelar" onclick="controlDownload('${safeFilename}', 'cancelar')"
                            style="padding: 6px 14px; font-size: 0.55rem; font-family: 'Press Start 2P', cursive;
                                   background: #e84118; color: #fff; border: 2px solid #fff;
                                   box-shadow: 2px 2px 0px #000; cursor: pointer;">
                             CANCELAR
                        </button>
                    </div>`;
                } else if (isError) {
                    // Show error detail if available
                    const errorDetail = d.detalle ? `<div style="color:#e84118; font-size:0.55rem; margin-top:6px; font-family:monospace; word-break:break-word; opacity:0.8;">${d.detalle}</div>` : '';
                    actionButtons = `
                    ${errorDetail}
                    <div style="display: flex; gap: 8px; margin-top: 14px; justify-content: flex-end; flex-wrap: wrap;">
                        <button data-file="${safeFilename}" data-action="reintentar" onclick="controlDownload('${safeFilename}', 'reintentar')"
                            style="padding: 6px 14px; font-size: 0.55rem; font-family: 'Press Start 2P', cursive;
                                   background: #fbc531; color: #000; border: 2px solid #fff;
                                   box-shadow: 2px 2px 0px #000; cursor: pointer;">
                             REINTENTAR
                        </button>
                        <button data-file="${safeFilename}" data-action="limpiar" onclick="controlDownload('${safeFilename}', 'limpiar')"
                            style="padding: 6px 14px; font-size: 0.55rem; font-family: 'Press Start 2P', cursive;
                                   background: #636e72; color: #fff; border: 2px solid #fff;
                                   box-shadow: 2px 2px 0px #000; cursor: pointer;">
                             LIMPIAR
                        </button>
                    </div>`;
                } else if (isComplete) {
                    actionButtons = `
                    <div style="display: flex; gap: 8px; margin-top: 14px; justify-content: flex-end;">
                        <button data-file="${safeFilename}" data-action="limpiar" onclick="controlDownload('${safeFilename}', 'limpiar')"
                            style="padding: 6px 14px; font-size: 0.55rem; font-family: 'Press Start 2P', cursive;
                                   background: #4cd137; color: #000; border: 2px solid #fff;
                                   box-shadow: 2px 2px 0px #000; cursor: pointer;">
                             LIMPIAR
                        </button>
                    </div>`;
                }

                html += `
                <div style="background: ${bgColor}; padding: 16px 18px; border-radius: 6px; margin-bottom: 14px;
                            width: 100%; box-sizing: border-box; border: 2px solid ${borderColor};
                            transition: border-color 0.3s ease;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; flex-wrap: wrap; gap: 6px;">
                        <span style="color: #fbc531; font-weight: bold; font-size: 0.7rem; word-break: break-all; flex: 1;">
                            ${statusIcon} ${filename}${consoleBadge}
                        </span>
                        <span style="color: ${barColor}; font-size: 0.65rem; font-family: 'Press Start 2P', cursive; white-space: nowrap;">
                            ${d.progress}% — ${statusLabel}
                        </span>
                    </div>
                    <div style="width: 100%; background: #1e242a; border-radius: 3px; height: 10px; overflow: hidden; border: 1px solid #444;">
                        <div style="width: ${d.progress}%; background: ${barColor}; height: 100%;
                                    transition: width 0.5s ease; ${progressAnimation}"></div>
                    </div>
                    ${(() => {
                        if (!isComplete && !isError) {
                            const spd = formatSpeed(d.dlspeed);
                            const eta = formatETA(d.eta);
                            if (spd || eta) {
                                return `<div style="display:flex; gap:16px; margin-top:8px; font-size:0.55rem;
                                                   color:#a0a0a0; font-family:'Press Start 2P',cursive;">
                                    ${spd ? `<span>⇩ ${spd}</span>` : ''}
                                    ${eta ? `<span> ${eta}</span>` : ''}
                                </div>`;
                            }
                        }
                        return '';
                    })()}
                    ${actionButtons}
                </div>`;
            });

            downloadsView.innerHTML = html;
            if (focusedFile && focusedAction) {
                // Escapar comillas simples para la consulta del selector
                const safeFileQuery = focusedFile.replace(/'/g, "\\'");
                const nextBtn = downloadsView.querySelector(`button[data-file="${safeFileQuery}"][data-action="${focusedAction}"]`);
                if (nextBtn) {
                    focusElement(nextBtn);
                }
            }
        }).catch(err => {
            console.error("Fetch error:", err);
            downloadsView.innerHTML = '<p style="color: #e84118; padding: 20px;">Error obteniendo descargas.</p>';
        });
    }
    
    fetchDownloads();
    downloadInterval = setInterval(fetchDownloads, 2000);
  }

  function showSettingsView() {
    updateNav(navSettings);
    viewTitle.textContent = "CONFIGURACION DEL SISTEMA";
    dynamicGrid.classList.add('hidden');
    settingsView.classList.remove('hidden');
    if (refreshLibraryBtn) refreshLibraryBtn.classList.add('hidden');
    
    // 1. Obtener y poblar dispositivos de audio PipeWire
    fetch(`${API_BASE_URL}/audio/dispositivos`)
      .then(res => res.json())
      .then(data => {
          if (data.estado === "OK" && data.dispositivos) {
              audioSelect.innerHTML = '';
              data.dispositivos.forEach(dev => {
                  const opt = document.createElement('option');
                  opt.value = dev.name;
                  opt.textContent = dev.description.toUpperCase();
                  audioSelect.appendChild(opt);
              });
              
              const savedAudio = localStorage.getItem('retro_selected_audio');
              if (savedAudio && Array.from(audioSelect.options).some(o => o.value === savedAudio)) {
                  audioSelect.value = savedAudio;
              }
          } else {
              audioSelect.innerHTML = '<option value="">ERROR AL OBTENER DISPOSITIVOS</option>';
          }
      }).catch(err => {
          console.error("Error obteniendo audio:", err);
          audioSelect.innerHTML = '<option value="">ERROR DE RED</option>';
      });

    // 2. Obtener pantallas, luego obtener ajustes del backend y popular UI
    fetch(`${API_BASE_URL}/pantallas`)
      .then(res => res.json())
      .then(data => {
          const targetSelDual = document.getElementById('cfg-target-monitor-dual');
          const hostSelSingle = document.getElementById('cfg-host-monitor-single');
          const hostSelDual = document.getElementById('cfg-host-monitor-dual');
          const hostSelStream = document.getElementById('cfg-host-monitor-stream');
          
          if (data.estado === "OK" && data.pantallas) {
              if (targetSelDual) targetSelDual.innerHTML = '';
              if (hostSelSingle) hostSelSingle.innerHTML = '';
              if (hostSelDual) hostSelDual.innerHTML = '';
              if (hostSelStream) hostSelStream.innerHTML = '';
              
              data.pantallas.forEach(p => {
                  if (targetSelDual) {
                      const opt = document.createElement('option');
                      opt.value = p;
                      opt.textContent = p;
                      targetSelDual.appendChild(opt);
                  }
                  if (hostSelSingle) {
                      const opt = document.createElement('option');
                      opt.value = p;
                      opt.textContent = p;
                      hostSelSingle.appendChild(opt);
                  }
                  if (hostSelDual) {
                      const opt = document.createElement('option');
                      opt.value = p;
                      opt.textContent = p;
                      hostSelDual.appendChild(opt);
                  }
                  if (hostSelStream) {
                      const opt = document.createElement('option');
                      opt.value = p;
                      opt.textContent = p;
                      hostSelStream.appendChild(opt);
                  }
              });
          }
          return fetch(`${API_BASE_URL}/ajustes`);
      })
      .then(res => res.json())
      .then(settings => {
          activeSettings = settings;
          if (activeSettings && activeSettings.controls) {
              activeSettings.controls.player1_profile = activeSettings.controls.player1_profile || "gamepad";
              activeSettings.controls.player2_profile = activeSettings.controls.player2_profile || "gamepad2";
              activeSettings.controls.player3_profile = activeSettings.controls.player3_profile || "gamepad3";
              activeSettings.controls.player4_profile = activeSettings.controls.player4_profile || "gamepad4";

              if (!activeSettings.controls.gamepad2) {
                  activeSettings.controls.gamepad2 = Object.assign({}, activeSettings.controls.gamepad || {});
              }
              if (!activeSettings.controls.gamepad3) {
                  activeSettings.controls.gamepad3 = Object.assign({}, activeSettings.controls.gamepad || {});
              }
              if (!activeSettings.controls.gamepad4) {
                  activeSettings.controls.gamepad4 = Object.assign({}, activeSettings.controls.gamepad || {});
              }
          }
          
          // Popular Video
          if (document.getElementById('cfg-crt')) document.getElementById('cfg-crt').checked = settings.video.crt_shader;
          if (document.getElementById('cfg-bilinear')) document.getElementById('cfg-bilinear').checked = settings.video.bilinear_filtering;
          if (document.getElementById('cfg-fps')) document.getElementById('cfg-fps').checked = settings.video.show_fps;
          if (document.getElementById('cfg-aspect')) document.getElementById('cfg-aspect').value = settings.video.aspect_ratio;
          
          // Popular Versatilidad
          let loadedMode = 'single';
          if (settings.versatility.target_monitor === 'TV-STREAM' && settings.versatility.target_workspace === '10') {
              loadedMode = 'stream';
          } else if (settings.versatility.target_workspace !== '1' || settings.versatility.target_monitor !== settings.versatility.host_monitor) {
              loadedMode = 'dual';
          }
          
          if (typeof window.setSettingsScreenMode === 'function') {
              window.setSettingsScreenMode(loadedMode);
          } else {
              window._settingsScreenMode = loadedMode;
          }
          
          if (document.getElementById('cfg-workspace-dual')) document.getElementById('cfg-workspace-dual').value = settings.versatility.target_workspace;
          if (document.getElementById('cfg-target-monitor-dual')) document.getElementById('cfg-target-monitor-dual').value = settings.versatility.target_monitor;
          if (document.getElementById('cfg-host-monitor-dual')) document.getElementById('cfg-host-monitor-dual').value = settings.versatility.host_monitor;
          if (document.getElementById('cfg-host-monitor-single')) document.getElementById('cfg-host-monitor-single').value = settings.versatility.host_monitor;
          if (document.getElementById('cfg-host-monitor-stream')) document.getElementById('cfg-host-monitor-stream').value = settings.versatility.host_monitor;
          
          // Sincronizar inputs ocultos por retrocompatibilidad
          if (document.getElementById('cfg-workspace')) document.getElementById('cfg-workspace').value = settings.versatility.target_workspace;
          if (document.getElementById('cfg-target-monitor')) document.getElementById('cfg-target-monitor').value = settings.versatility.target_monitor;
          if (document.getElementById('cfg-host-monitor')) document.getElementById('cfg-host-monitor').value = settings.versatility.host_monitor;
          
          // Popular emuladores standalone
          const emus = settings.emulators || {};
          if (document.getElementById('emu-ps1')) document.getElementById('emu-ps1').value = emus.ps1 || 'retroarch';
          if (document.getElementById('emu-ps2')) document.getElementById('emu-ps2').value = emus.ps2 || 'pcsx2';
          if (document.getElementById('emu-gamecube')) document.getElementById('emu-gamecube').value = emus.gamecube || 'dolphin';
          if (document.getElementById('emu-wii')) document.getElementById('emu-wii').value = emus.wii || 'dolphin';
          if (document.getElementById('emu-xbox')) document.getElementById('emu-xbox').value = emus.xbox || 'xemu';
          if (document.getElementById('emu-psp')) document.getElementById('emu-psp').value = emus.psp || 'ppsspp';

          // Popular tema
          const themeSelector = document.getElementById('cfg-theme');
          if (themeSelector) {
              const currentTheme = settings.theme || localStorage.getItem('retro_theme') || 'neon';
              themeSelector.value = currentTheme;
              document.body.setAttribute('data-theme', currentTheme);
          }

          // Popular Ruta de ROMs
          if (document.getElementById('cfg-roms-path')) {
              document.getElementById('cfg-roms-path').value = settings.roms_path || '';
          }

          // Popular Mapeo Perfil
          populateProfilesSelect(settings.controls.profile);
          
          // Renderizar grilla de mapeos
          renderMappingGrid();

          // Comprobar Setup Wizard (primer arranque)
          if (settings.first_run) {
              startSetupWizard();
          }
      })
      .catch(err => console.error("Error cargando pantallas o ajustes del backend:", err));
  }

  const GAMEPAD_KEY_ORDER = [
      "dpup", "dpdown", "dpleft", "dpright",
      "a", "b", "x", "y",
      "back", "start", "guide",
      "leftstick", "rightstick",
      "leftshoulder", "rightshoulder",
      "lefttrigger", "righttrigger"
  ];

  const KEYBOARD_KEY_ORDER = [
      "up", "down", "left", "right",
      "a", "b", "x", "y",
      "select", "start", "guide",
      "l1", "r1", "l2", "r2"
  ];

  function renderMappingGrid() {
      const mappingGrid = document.getElementById('mapping-grid');
      if (!mappingGrid || !activeSettings) return;
      
      mappingGrid.innerHTML = '';
      const profile = document.getElementById('cfg-profile').value;
      const controlsObj = activeSettings.controls[profile] || {};
      
      const keyOrder = (profile === 'keyboard') ? KEYBOARD_KEY_ORDER : GAMEPAD_KEY_ORDER;
      const sortedKeys = Object.keys(controlsObj).sort((a, b) => {
          const indexA = keyOrder.indexOf(a);
          const indexB = keyOrder.indexOf(b);
          if (indexA === -1 && indexB === -1) return 0;
          if (indexA === -1) return 1;
          if (indexB === -1) return -1;
          return indexA - indexB;
      });
      
      sortedKeys.forEach(actionKey => {
          const lookupKey = `${profile}_${actionKey}`;
          const displayName = CONTROL_DISPLAY_NAMES[lookupKey] || CONTROL_DISPLAY_NAMES[actionKey] || actionKey.toUpperCase();
          const bindValue = controlsObj[actionKey];
          
          const row = document.createElement('div');
          row.style.display = 'flex';
          row.style.alignItems = 'center';
          row.style.justifyContent = 'space-between';
          row.style.background = 'rgba(255,255,255,0.03)';
          row.style.padding = '8px 12px';
          row.style.borderRadius = 'var(--border-radius-md)';
          row.style.border = '1px solid rgba(255,255,255,0.03)';
          row.style.fontFamily = "'Press Start 2P', cursive";
          row.style.fontSize = '0.55rem';
          
          const labelSpan = document.createElement('span');
          labelSpan.style.color = '#ccc';
          labelSpan.textContent = displayName;
          
          const bindButton = document.createElement('button');
          bindButton.className = 'btn-secondary';
          bindButton.style.padding = '4px 10px';
          bindButton.style.fontFamily = "'Press Start 2P'";
          bindButton.style.fontSize = '0.55rem';
          bindButton.style.minWidth = '80px';
          
          if (currentMappingAction === actionKey) {
              bindButton.textContent = 'PULSAR...';
              bindButton.style.background = 'var(--accent-gold)';
              bindButton.style.color = '#000';
          } else {
              bindButton.textContent = String(bindValue).toUpperCase();
              bindButton.style.background = 'rgba(0,0,0,0.4)';
              bindButton.style.color = 'var(--accent-cyan)';
          }
          
          bindButton.addEventListener('click', (e) => {
              e.preventDefault();
              currentMappingAction = actionKey;
              renderMappingGrid();
          });
          
          row.appendChild(labelSpan);
          row.appendChild(bindButton);
          mappingGrid.appendChild(row);
      });
  }

  // Capturador de teclado para binds
  window.addEventListener('keydown', (e) => {
      const profileSelect = document.getElementById('cfg-profile');
      if (currentMappingAction && profileSelect && profileSelect.value === 'keyboard') {
          e.preventDefault();
          const key = e.key.toLowerCase();
          activeSettings.controls.keyboard[currentMappingAction] = key;
          currentMappingAction = null;
          renderMappingGrid();
      }
  });

  function applyFilters(resetPage = true) {
    if (resetPage) {
        currentPage = 1;
    }
    const query = searchInput.value.toLowerCase();
    const consoleVal = consoleFilter.value;
    const sortVal = sortFilter ? sortFilter.value : 'default';

    if (isCatalogMode) {
      let url = `${API_BASE_URL}/catalogo?page=${currentPage}&per_page=${ITEMS_PER_PAGE}`;
      if (query.trim() !== "") url += `&q=${encodeURIComponent(query)}`;
      if (consoleVal !== "all") url += `&console=${encodeURIComponent(consoleVal)}`;
      if (sortVal !== "default") url += `&sort=${encodeURIComponent(sortVal)}`;
      
      fetch(url)
        .then(res => res.json())
        .then(data => {
          if (data.estado === 'OK') {
            renderGameCardsServer(data.resultados, data.total, isCatalogMode);
          }
        })
        .catch(err => console.error("Error querying catalog:", err));
      return;
    }

    let source = [];
    if (navLocal.classList.contains('active')) source = localGames;
    else if (navFavorites.classList.contains('active')) {
      const allKnown = [...localGames, ...catalogGames];
      const favs = allKnown.filter(g => favorites.includes(g.title));
      const uniqueFavs = [];
      const seen = new Set();
      favs.forEach(f => {
          if(!seen.has(f.title)) {
              seen.add(f.title);
              uniqueFavs.push(f);
          }
      });
      source = uniqueFavs;
    }
    else return;

    const filtered = source.filter(g => {
      const matchesText = g.title.toLowerCase().includes(query);
      const matchesConsole = (consoleVal === 'all') || (g.console === consoleVal);
      return matchesText && matchesConsole;
    });

    if (sortVal === 'popularity') {
        filtered.sort((a, b) => (b.popularity_score || 0) - (a.popularity_score || 0));
    } else if (sortVal === 'name-asc') {
        filtered.sort((a, b) => a.title.localeCompare(b.title));
    } else if (sortVal === 'name-desc') {
        filtered.sort((a, b) => b.title.localeCompare(a.title));
    } else if (sortVal === 'size-desc' || sortVal === 'size-asc') {
        const parseSize = (game) => {
            if (!game.versions || game.versions.length === 0) return 0;
            const sizeStr = (game.versions[0].size || "").toUpperCase();
            let val = parseFloat(sizeStr) || 0;
            if (sizeStr.includes('GB')) val *= 1024 * 1024 * 1024;
            else if (sizeStr.includes('MB')) val *= 1024 * 1024;
            else if (sizeStr.includes('KB')) val *= 1024;
            return val;
        };
        filtered.sort((a, b) => {
            const sizeA = parseSize(a);
            const sizeB = parseSize(b);
            return sortVal === 'size-desc' ? sizeB - sizeA : sizeA - sizeB;
        });
    }

    renderGameCards(filtered, isCatalogMode);
  }

  function renderGameCardsServer(games, totalItems, asCatalog = false) {
    renderLastPlayed();
    dynamicGrid.innerHTML = '';
    
    if (games.length === 0) {
      dynamicGrid.innerHTML = '<p style="color:#a0a0a0; padding: 2rem;">No hay juegos aquí.</p>';
      renderPaginationControlsServer(0, 0, asCatalog);
      return;
    }

    games.forEach(game => {
      const card = document.createElement('div');
      card.className = 'game-card';
      const imgSrc = game.image || 'https://placehold.co/200x250/2f3640/fbc531?text=NO+COVER';
      
      let badge = '';
      if (asCatalog && game.downloaded) {
          badge = '<div style="position:absolute; top:5px; right:5px; background: #4cd137; padding: 2px 5px; border-radius:3px; color:white; font-size:10px;"> LISTO</div>';
      }

      card.innerHTML = `
        <img src="${imgSrc}" alt="${game.title}" data-title="${game.title}" data-console="${game.console}" onerror="handleCoverError(this)">
        ${badge}
        <h3>${game.title}</h3>
      `;
      card.addEventListener('click', () => openModal(game, asCatalog));
      dynamicGrid.appendChild(card);
    });

    const totalPages = Math.ceil(totalItems / ITEMS_PER_PAGE);
    renderPaginationControlsServer(totalItems, totalPages, asCatalog);

    if (document.body.classList.contains('couch-mode')) {
        setTimeout(() => {
            if (!focusedElement || focusedElement.classList.contains('nav-btn') || !document.body.contains(focusedElement)) {
                const firstCard = dynamicGrid.querySelector('.game-card');
                if (firstCard) focusElement(firstCard);
            }
        }, 150);
    }
  }

  function renderPaginationControlsServer(totalItems, totalPages, asCatalog) {
    let paginationContainer = document.getElementById('pagination-controls');
    if (!paginationContainer) {
        paginationContainer = document.createElement('div');
        paginationContainer.id = 'pagination-controls';
        paginationContainer.style = 'display: flex; justify-content: center; gap: 1rem; padding: 2rem; width: 100%;';
        dynamicGrid.parentNode.insertBefore(paginationContainer, dynamicGrid.nextSibling);
    }
    
    paginationContainer.innerHTML = '';
    
    if (totalPages <= 1) return;

    const prevBtn = document.createElement('button');
    prevBtn.textContent = '◄ ANTERIOR';
    prevBtn.className = 'action-btn';
    prevBtn.disabled = currentPage === 1;
    prevBtn.onclick = () => {
        if (currentPage > 1) {
            currentPage--;
            applyFilters(false);
        }
    };

    const pageIndicator = document.createElement('span');
    pageIndicator.textContent = `PAGINA ${currentPage} DE ${totalPages}`;
    pageIndicator.style = "font-family: 'Press Start 2P', cursive; font-size: 0.6rem; color: var(--text-secondary); display: flex; align-items: center;";

    const nextBtn = document.createElement('button');
    nextBtn.textContent = 'SIGUIENTE ►';
    nextBtn.className = 'action-btn';
    nextBtn.disabled = currentPage === totalPages;
    nextBtn.onclick = () => {
        if (currentPage < totalPages) {
            currentPage++;
            applyFilters(false);
        }
    };

    paginationContainer.appendChild(prevBtn);
    paginationContainer.appendChild(pageIndicator);
    paginationContainer.appendChild(nextBtn);
  }

  function showCatalogView() {
    updateNav(navCatalog);
    viewTitle.textContent = 'REPOSITORIO DE ROMS';
    backBtn.classList.add('hidden');
    if (refreshLibraryBtn) refreshLibraryBtn.classList.add('hidden');
    isCatalogMode = true;
    applyFilters();
  }

  function showLocalView() {
    updateNav(navLocal);
    viewTitle.textContent = 'LIBRERIA LOCAL';
    backBtn.classList.add('hidden');
    if (refreshLibraryBtn) refreshLibraryBtn.classList.remove('hidden');
    isCatalogMode = false;
    
    // Refresh local library data every time the tab is opened
    fetch(`${API_BASE_URL}/libreria`)
      .then(res => res.json())
      .then(data => {
        localGames = data;
        applyFilters();
      }).catch(err => {
        console.error("Error updating local library:", err);
        applyFilters(); // fallback to cached data
      });
  }

  function showFavoritesView() {
    updateNav(navFavorites);
    viewTitle.textContent = 'FAVORITOS';
    backBtn.classList.add('hidden');
    if (refreshLibraryBtn) refreshLibraryBtn.classList.add('hidden');
    isCatalogMode = false;
    applyFilters();
  }

  // Búsqueda en tiempo real
  searchInput.addEventListener('input', applyFilters);
  searchInput.addEventListener('click', () => {
      if (document.body.classList.contains('couch-mode')) {
          showVirtualKeyboard();
      }
  });
  consoleFilter.addEventListener('change', applyFilters);
  if (sortFilter) sortFilter.addEventListener('change', applyFilters);

  // --- Controlador de imágenes de portada con fallbacks ---
  window.handleCoverError = function(img) {
      if (img.getAttribute('data-fallback-step') === 'done') {
          img.src = 'https://placehold.co/200x250/2f3640/fbc531?text=Sin+Portada';
          return;
      }
      
      const title = img.getAttribute('data-title');
      const consoleName = img.getAttribute('data-console');
      if (!title || !consoleName) {
          img.setAttribute('data-fallback-step', 'done');
          img.src = 'https://placehold.co/200x250/2f3640/fbc531?text=Sin+Portada';
          return;
      }

      const step = parseInt(img.getAttribute('data-fallback-step') || '0');
      img.setAttribute('data-fallback-step', step + 1);
      
      const mapping = {
        "snes": "Nintendo - Super Nintendo Entertainment System",
        "nes": "Nintendo - Nintendo Entertainment System",
        "n64": "Nintendo - Nintendo 64",
        "gb": "Nintendo - Game Boy",
        "gbc": "Nintendo - Game Boy Color",
        "gba": "Nintendo - Game Boy Advance",
        "megadrive": "Sega - Mega Drive - Genesis",
        "mastersystem": "Sega - Master System - Mark III",
        "gamegear": "Sega - Game Gear",
        "nds": "Nintendo - Nintendo DS",
        "ps1": "Sony - PlayStation",
        "ps2": "Sony - PlayStation 2",
        "ps3": "Sony - PlayStation 3",
        "psp": "Sony - PlayStation Portable",
        "gamecube": "Nintendo - GameCube",
        "xbox": "Microsoft - Xbox",
        "xbox360": "Microsoft - Xbox 360",
        "wii": "Nintendo - Wii",
        "3ds": "Nintendo - Nintendo 3DS",
        "wiiu": "Nintendo - Wii U",
        "switch": "Nintendo - Nintendo Switch",
        "saturn": "Sega - Saturn",
        "dreamcast": "Sega - Dreamcast"
      };
      
      const system = mapping[consoleName];
      if (!system) {
          img.setAttribute('data-fallback-step', 'done');
          img.src = 'https://placehold.co/200x250/2f3640/fbc531?text=Sin+Portada';
          return;
      }

      // Helper: strip all region/version/disc/language parentheses from a title
      const stripAll = (t) => t.replace(/\s*\(.*?\)/g, '').replace(/\s*\[.*?\]/g, '').trim();
      // Helper: strip only language/version/disc tags but keep region
      const stripLangVer = (t) => t.replace(/\s*\((?:En|Fr|De|Es|It|Pt|Nl|Sv|No|Da|Fi|Pl|Ru|Zh|Ko|Ja|Asia|v[\d.]+|Disc \d+)[^)]*\)/gi, '').trim();
      // Helper: strip subtitle after " - " from stripped base name
      const stripSubtitle = (t) => t.replace(/\s[-–—]\s.*$/, '').replace(/:\s.*$/, '').trim();
      // Helper: move leading article (The, A, An) to end
      const moveArticle = (t) => {
          const m = t.match(/^(The|A|An)\s+(.+)$/i);
          return m ? `${m[2]}, ${m[1]}` : t;
      };

      const base = stripAll(title);

      let nextTitle;
      switch (step) {
          case 0:  // Strip lang/version/disc tags only (keep region)
              nextTitle = stripLangVer(title);
              break;
          case 1:  // Strip ALL parentheses/brackets
              nextTitle = base;
              break;
          case 2:  // Base + (USA)
              nextTitle = `${base} (USA)`;
              break;
          case 3:  // Base + (Europe)
              nextTitle = `${base} (Europe)`;
              break;
          case 4:  // Base + (Japan)
              nextTitle = `${base} (Japan)`;
              break;
          case 5:  // Base + (Asia)
              nextTitle = `${base} (Asia)`;
              break;
          case 6:  // Strip subtitle after " - " or ":" (keep region from original)
              nextTitle = stripLangVer(title);
              nextTitle = stripSubtitle(nextTitle);
              break;
          case 7:  // Full strip + strip subtitle
              nextTitle = stripSubtitle(base);
              break;
          case 8:  // Move leading article ("The X" → "X, The")
              nextTitle = moveArticle(base);
              break;
          case 9:  // Article move + (USA)
              nextTitle = `${moveArticle(base)} (USA)`;
              break;
          default:
              img.setAttribute('data-fallback-step', 'done');
              img.src = 'https://placehold.co/200x250/2f3640/fbc531?text=Sin+Portada';
              return;
      }
      
      const cleanTitle = nextTitle.replace('&', '_');
      img.src = `https://thumbnails.libretro.com/${encodeURIComponent(system)}/Named_Boxarts/${encodeURIComponent(cleanTitle)}.png`;
  };

  let currentPage = 1;
  const ITEMS_PER_PAGE = 50;

  function renderGameCards(games, asCatalog = false, resetPage = true) {
    if (resetPage) currentPage = 1;
    renderLastPlayed();
    dynamicGrid.innerHTML = '';
    
    if (games.length === 0) {
      dynamicGrid.innerHTML = '<p style="color:#a0a0a0; padding: 2rem;">No hay juegos aquí.</p>';
      renderPaginationControls(0, 0, games, asCatalog);
      return;
    }

    const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
    const endIndex = startIndex + ITEMS_PER_PAGE;
    const paginatedGames = games.slice(startIndex, endIndex);

    paginatedGames.forEach(game => {
      const card = document.createElement('div');
      card.className = 'game-card';
      const imgSrc = game.image || 'https://placehold.co/200x250/2f3640/fbc531?text=NO+COVER';
      
      let badge = '';
      if (asCatalog && game.downloaded) {
          badge = '<div style="position:absolute; top:5px; right:5px; background: #4cd137; padding: 2px 5px; border-radius:3px; color:white; font-size:10px;"> LISTO</div>';
      }

      card.innerHTML = `
        <img src="${imgSrc}" alt="${game.title}" data-title="${game.title}" data-console="${game.console}" onerror="handleCoverError(this)">
        ${badge}
        <h3>${game.title}</h3>
      `;
      card.addEventListener('click', () => openModal(game, asCatalog));
      dynamicGrid.appendChild(card);
    });

    renderPaginationControls(games.length, Math.ceil(games.length / ITEMS_PER_PAGE), games, asCatalog);

    // Auto-enfocar el primer elemento de la grilla en Modo Tele si es necesario
    if (document.body.classList.contains('couch-mode')) {
        setTimeout(() => {
            if (!focusedElement || focusedElement.classList.contains('nav-btn') || !document.body.contains(focusedElement)) {
                const firstCard = dynamicGrid.querySelector('.game-card');
                if (firstCard) focusElement(firstCard);
            }
        }, 150);
    }
  }

  function renderPaginationControls(totalItems, totalPages, games, asCatalog) {
    let paginationContainer = document.getElementById('pagination-controls');
    if (!paginationContainer) {
        paginationContainer = document.createElement('div');
        paginationContainer.id = 'pagination-controls';
        paginationContainer.style = 'display: flex; justify-content: center; gap: 1rem; padding: 2rem; width: 100%;';
        dynamicGrid.parentNode.insertBefore(paginationContainer, dynamicGrid.nextSibling);
    }
    
    paginationContainer.innerHTML = '';
    
    if (totalPages <= 1) return;

    const prevBtn = document.createElement('button');
    prevBtn.textContent = '◄ ANTERIOR';
    prevBtn.className = 'action-btn';
    prevBtn.disabled = currentPage === 1;
    prevBtn.onclick = () => {
        if (currentPage > 1) {
            currentPage--;
            renderGameCards(games, asCatalog, false);
            window.scrollTo(0, 0);
        }
    };

    const info = document.createElement('span');
    info.textContent = ` Pág. ${currentPage} de ${totalPages} `;
    info.style = 'color: white; line-height: 40px; font-family: "Press Start 2P"; font-size: 0.7rem;';

    const nextBtn = document.createElement('button');
    nextBtn.textContent = 'SIGUIENTE ►';
    nextBtn.className = 'action-btn';
    nextBtn.disabled = currentPage === totalPages;
    nextBtn.onclick = () => {
        if (currentPage < totalPages) {
            currentPage++;
            renderGameCards(games, asCatalog, false);
            window.scrollTo(0, 0);
        }
    };

    paginationContainer.appendChild(prevBtn);
    paginationContainer.appendChild(info);
    paginationContainer.appendChild(nextBtn);
  }

  // --- Favoritos ---
  function updateHeartButton() {
      if (currentGame && favorites.includes(currentGame.title)) {
          favBtn.textContent = '';
      } else {
          favBtn.textContent = '';
      }
  }

  favBtn.addEventListener('click', () => {
      if (!currentGame) return;
      if (favorites.includes(currentGame.title)) {
          favorites = favorites.filter(f => f !== currentGame.title);
      } else {
          favorites.push(currentGame.title);
      }
      localStorage.setItem('retro_favorites', JSON.stringify(favorites));
      updateHeartButton();
  });


  // --- Modal y Acciones ---
  function openModal(game, asCatalog = false) {
    currentGame = game;
    modalImg.setAttribute('data-title', game.title);
    modalImg.setAttribute('data-console', game.console);
    modalImg.removeAttribute('data-fallback-step');
    modalImg.src = game.image || 'https://placehold.co/200x250/2f3640/fbc531?text=NO+COVER';
    modalImg.onerror = function() {
        handleCoverError(this);
    };
    modalTitle.textContent = game.title;
    modalStatus.textContent = '';
    
    // Restablecer el estado del botón de borrar
    deleteBtn.disabled = false;
    deleteBtn.textContent = ' BORRAR';
    
    updateHeartButton();

    if (asCatalog) {
      // Modo Catálogo IA
      modalYear.textContent = game.console;
      versionContainer.classList.remove('hidden');
      versionSelect.innerHTML = '';
      game.versions.forEach((v, index) => {
          const opt = document.createElement('option');
          opt.value = index;
          opt.textContent = `${v.versionName} (${v.size})`;
          versionSelect.appendChild(opt);
      });
      
      playBtn.classList.add('hidden');
      downloadBtn.classList.remove('hidden');
      deleteBtn.classList.add('hidden');
      downloadBtn.disabled = game.downloaded;
      downloadBtn.textContent = game.downloaded ? ' INSTALADO' : ' DESCARGAR';

    } else {
      // Modo Local / Jugar
      // Check if it's actually a local game format
      if (!game.path) {
          // If a catalog game was opened from favorites
          modalYear.textContent = "REPOSITORIO DE ROMS";
          versionContainer.classList.add('hidden');
          playBtn.classList.add('hidden');
          downloadBtn.classList.remove('hidden');
          deleteBtn.classList.add('hidden');
          downloadBtn.disabled = true;
          downloadBtn.textContent = 'BUSCA EN REPOSITORIO';
      } else {
          modalYear.textContent = `${game.console} • LOCAL`;
          versionContainer.classList.add('hidden');
          playBtn.classList.remove('hidden');
          downloadBtn.classList.add('hidden');
          deleteBtn.classList.remove('hidden');
          playBtn.disabled = false;
          playBtn.textContent = '▶ JUGAR';
      }
    }
    
    modal.classList.remove('hidden');
  }

  function closeModal() {
    modal.classList.add('hidden');
    currentGame = null;
  }

  playBtn.addEventListener('click', () => {
    if (!currentGame) return;
    playBtn.textContent = 'INIT...';
    playBtn.disabled = true;
    modalStatus.textContent = 'Ejecutando SSH...';

    // Establecer de inmediato para evitar que el click propague e intente hacer fullscreen en la web robando foco
    isGamePlaying = true;
    stopGamepadPolling();

    const apiUrl = `${API_BASE_URL}/jugar?core=${encodeURIComponent(currentGame.core)}&rom_path=${encodeURIComponent(currentGame.path)}&console=${encodeURIComponent(currentGame.console)}`;
    fetch(apiUrl)
      .then(res => res.json())
      .then(data => {
        if (data.estado === 'OK') {
          modalStatus.textContent = '>> EXITOSO <<';
          
          const lastPlayed = {
              title: currentGame.title,
              console: currentGame.console,
              image: currentGame.image,
              core: currentGame.core,
              path: currentGame.path,
              timestamp: Date.now()
          };
          localStorage.setItem('retro_last_played', JSON.stringify(lastPlayed));
          renderLastPlayed();
          
          closeModal();
          
          // Esperar 8 segundos de gracia para dar tiempo al emulador a arrancar y registrar su proceso
          setTimeout(() => {
              let checkGameInterval = setInterval(() => {
                  fetch(`${API_BASE_URL}/estado_emulador`)
                    .then(res => res.json())
                    .then(dataCheck => {
                        if (!dataCheck.activo) {
                            clearInterval(checkGameInterval);
                            isGamePlaying = false;
                            isGamePaused = false;
                            const banner = document.getElementById('game-paused-banner');
                            if (banner) banner.classList.add('hidden');
                            startGamepadPolling();
                            // Enfocar de nuevo el navegador en el host para reactivar los eventos de gamepad de Chromium
                            fetch(`${API_BASE_URL}/foco`).catch(err => console.error("Error enfocando browser:", err));
                            // Refrescar libreria y enfocar primera tarjeta
                            setTimeout(() => {
                                const first = document.querySelector('.game-card');
                                if (first) focusElement(first);
                            }, 500);
                        }
                    }).catch(err => {
                        console.error("Error comprobando estado del emulador:", err);
                    });
              }, 2000);
          }, 8000);
        } else {
          isGamePlaying = false;
          startGamepadPolling();
          modalStatus.textContent = 'ERR: ' + data.detalle;
          playBtn.disabled = false;
        }
      }).catch(err => {
        isGamePlaying = false;
        startGamepadPolling();
        modalStatus.textContent = 'ERR DE RED';
        playBtn.disabled = false;
      });
  });

  downloadBtn.addEventListener('click', () => {
    if (!currentGame || !isCatalogMode) return;
    
    const selectedVersionIndex = versionSelect.value;
    const selectedVersion = currentGame.versions[selectedVersionIndex];

    downloadBtn.textContent = ' PREPARANDO...';
    downloadBtn.disabled = true;
    downloadBtn.style.background = '#dcdde1';
    downloadBtn.style.borderColor = '#7f8fa6';
    modalStatus.textContent = 'Contactando con qBittorrent...';

    let expectedSizeBytes = 0;
    const sizeStr = (selectedVersion.size || "").toUpperCase();
    if (sizeStr.includes('GB')) {
        expectedSizeBytes = parseFloat(sizeStr) * 1024 * 1024 * 1024;
    } else if (sizeStr.includes('MB')) {
        expectedSizeBytes = parseFloat(sizeStr) * 1024 * 1024;
    } else if (sizeStr.includes('KB')) {
        expectedSizeBytes = parseFloat(sizeStr) * 1024;
    }

    const urlTorrent = selectedVersion.downloadUrl;
    const apiUrl = `${API_BASE_URL}/descargar?url_torrent=${encodeURIComponent(urlTorrent)}&console=${encodeURIComponent(currentGame.console)}&expected_size=${Math.floor(expectedSizeBytes)}`;

    fetch(apiUrl)
      .then(res => res.json())
      .then(data => {
        if (data.estado === 'OK') {
          modalStatus.textContent = '>> AGREGADO A COLA CON EXITO <<';
          downloadBtn.textContent = ' ¡DESCARGANDO!';
          downloadBtn.style.background = '#2ecc71';
          downloadBtn.style.borderColor = '#27ae60';
          
          // Refrescar datos y cerrar el modal tras 2 segundos de feedback exitoso
          setTimeout(() => {
            loadData(false);
            closeModal();
            // Restaurar estilos del botón para la próxima vez
            downloadBtn.style.background = '';
            downloadBtn.style.borderColor = '';
          }, 2000);
        } else {
          modalStatus.textContent = 'ERR: ' + data.detalle;
          downloadBtn.disabled = false;
          downloadBtn.textContent = ' DESCARGAR';
          downloadBtn.style.background = '';
          downloadBtn.style.borderColor = '';
        }
      }).catch(err => {
        modalStatus.textContent = 'ERR DE RED';
        downloadBtn.disabled = false;
        downloadBtn.textContent = ' DESCARGAR';
        downloadBtn.style.background = '';
        downloadBtn.style.borderColor = '';
      });
  });

  deleteBtn.addEventListener('click', () => {
    if (!currentGame || isCatalogMode) return;
    
    showConfirmModal(`¿BORRAR PERMANENTEMENTE ${currentGame.title.toUpperCase()}?`, () => {
        deleteBtn.textContent = 'BORRANDO...';
        deleteBtn.disabled = true;
        modalStatus.textContent = 'Borrando juego...';

        const apiUrl = `${API_BASE_URL}/borrar?rom_path=${encodeURIComponent(currentGame.path)}`;
        fetch(apiUrl, { method: 'DELETE' })
          .then(res => res.json())
          .then(data => {
            if (data.estado === 'OK') {
              closeConfirmModal(true);
              closeModal();
              loadData(false); // Reload library
            } else {
              modalStatus.textContent = 'ERR: ' + data.detalle;
              deleteBtn.disabled = false;
              deleteBtn.textContent = ' BORRAR';
            }
          }).catch(err => {
            modalStatus.textContent = 'ERR DE RED';
            deleteBtn.disabled = false;
            deleteBtn.textContent = ' BORRAR';
          });
    }, () => {
        setTimeout(() => {
            focusElement(deleteBtn);
        }, 100);
    });
  });

  // --- Custom Modals & Selectors Helpers ---
  let confirmCallback = null;
  let cancelCallback = null;

  function showConfirmModal(message, onConfirm, onCancel) {
      isConfirmOpen = true;
      confirmTitle.textContent = message;
      confirmModal.classList.remove('hidden');
      confirmCallback = onConfirm;
      cancelCallback = onCancel;
      
      setTimeout(() => {
          focusElement(confirmNoBtn);
      }, 100);
  }

  function closeConfirmModal(success) {
      confirmModal.classList.add('hidden');
      isConfirmOpen = false;
      if (success && confirmCallback) {
          confirmCallback();
      } else if (!success && cancelCallback) {
          cancelCallback();
      }
      confirmCallback = null;
      cancelCallback = null;
  }

  confirmYesBtn.addEventListener('click', () => closeConfirmModal(true));
  confirmNoBtn.addEventListener('click', () => closeConfirmModal(false));

  function showCustomSelector(selectEl, titleText) {
      isSelectorOpen = true;
      activeSelectorEl = selectEl;
      selectorTitle.textContent = titleText;
      selectorOptionsGrid.innerHTML = '';
      
      const options = Array.from(selectEl.options);
      options.forEach(opt => {
          const btn = document.createElement('button');
          btn.className = 'select-option-btn';
          btn.textContent = opt.text.toUpperCase();
          
          if (opt.value === selectEl.value) {
              btn.classList.add('active-option');
          }
          
          btn.addEventListener('click', () => {
              selectEl.value = opt.value;
              selectEl.dispatchEvent(new Event('change'));
              hideCustomSelector();
          });
          
          selectorOptionsGrid.appendChild(btn);
      });
      
      selectorModal.classList.remove('hidden');
      
      setTimeout(() => {
          const activeBtn = selectorOptionsGrid.querySelector('.active-option');
          if (activeBtn) {
              focusElement(activeBtn);
          } else {
              const firstOpt = selectorOptionsGrid.querySelector('.select-option-btn');
              if (firstOpt) focusElement(firstOpt);
          }
      }, 100);
  }

  function hideCustomSelector() {
      if (!isSelectorOpen) return;
      selectorModal.classList.add('hidden');
      isSelectorOpen = false;
      const elToFocus = activeSelectorEl;
      activeSelectorEl = null;
      
      setTimeout(() => {
          if (elToFocus) focusElement(elToFocus);
      }, 100);
  }

  // --- Folder Explorer Modals and Helpers ---
  function openFolderExplorer(targetInputEl) {
      isExplorerOpen = true;
      activeExplorerTargetInput = targetInputEl;
      
      let initialPath = "";
      if (targetInputEl && targetInputEl.value) {
          initialPath = targetInputEl.value.trim();
      }
      
      // Si el input está vacío, no es una ruta absoluta, o contiene placeholders del .env o wizard, inicializar en Home (~)
      if (!initialPath || initialPath === "" || initialPath.includes("tu_disco") || initialPath.includes("usuario") || !initialPath.startsWith("/")) {
          initialPath = "~";
      }
      
      const folderExplorerModal = document.getElementById('folder-explorer-modal');
      if (folderExplorerModal) {
          folderExplorerModal.classList.remove('hidden');
      }
      
      loadExplorerPath(initialPath);
  }

  function closeFolderExplorer() {
      if (!isExplorerOpen) return;
      isExplorerOpen = false;
      const folderExplorerModal = document.getElementById('folder-explorer-modal');
      if (folderExplorerModal) {
          folderExplorerModal.classList.add('hidden');
      }
      
      const elToFocus = activeExplorerTargetInput;
      activeExplorerTargetInput = null;
      
      setTimeout(() => {
          if (elToFocus) focusElement(elToFocus);
      }, 150);
  }

  function loadExplorerPath(path) {
      let url = `${API_BASE_URL}/explorar`;
      if (path) {
          url += `?ruta=${encodeURIComponent(path)}`;
      }
      
      const explorerList = document.getElementById('explorer-list');
      const explorerCurrentPathEl = document.getElementById('explorer-current-path');
      
      if (explorerList) {
          explorerList.innerHTML = '<div style="color: #aaa; font-family: monospace; font-size: 0.8rem; padding: 10px;">Cargando directorios...</div>';
      }
      
      fetch(url)
          .then(res => res.json())
          .then(data => {
              if (data.estado === 'OK') {
                  explorerCurrentPath = data.ruta_actual;
                  if (explorerCurrentPathEl) {
                      explorerCurrentPathEl.textContent = explorerCurrentPath;
                  }
                  
                  if (!explorerList) return;
                  explorerList.innerHTML = '';
                  
                  // Botón para subir al directorio padre (..)
                  if (data.padre && data.padre !== explorerCurrentPath) {
                      const parentBtn = document.createElement('button');
                      parentBtn.className = 'select-option-btn';
                      parentBtn.style.padding = '12px';
                      parentBtn.style.fontSize = '0.65rem';
                      parentBtn.style.marginBottom = '4px';
                      parentBtn.innerHTML = '<span style="color: var(--accent-cyan);"> .. (Subir un nivel)</span>';
                      parentBtn.addEventListener('click', () => {
                          loadExplorerPath(data.padre);
                      });
                      explorerList.appendChild(parentBtn);
                  }
                  
                  // Listar los directorios devueltos
                  if (data.directorios && data.directorios.length > 0) {
                      data.directorios.forEach(dirName => {
                          const dirBtn = document.createElement('button');
                          dirBtn.className = 'select-option-btn';
                          dirBtn.style.padding = '12px';
                          dirBtn.style.fontSize = '0.65rem';
                          dirBtn.innerHTML = ` ${dirName}`;
                          dirBtn.addEventListener('click', () => {
                              const nextPath = explorerCurrentPath === '/' ? `/${dirName}` : `${explorerCurrentPath}/${dirName}`;
                              loadExplorerPath(nextPath);
                          });
                          explorerList.appendChild(dirBtn);
                      });
                  } else {
                      const emptyMsg = document.createElement('div');
                      emptyMsg.style.color = '#777';
                      emptyMsg.style.padding = '10px';
                      emptyMsg.style.fontFamily = "'Press Start 2P'";
                      emptyMsg.style.fontSize = '0.5rem';
                      emptyMsg.style.textAlign = 'center';
                      emptyMsg.textContent = 'NO HAY SUBDIRECTORIOS';
                      explorerList.appendChild(emptyMsg);
                  }
                  
                  // Auto-focus al primer elemento disponible para facilitar el control con joystick
                  setTimeout(() => {
                      const firstBtn = explorerList.querySelector('button');
                      if (firstBtn) {
                          focusElement(firstBtn);
                      } else {
                          const selectBtn = document.getElementById('explorer-select-btn');
                          if (selectBtn) focusElement(selectBtn);
                      }
                  }, 100);
              } else {
                  if (explorerList) {
                      explorerList.innerHTML = `<div style="color: var(--btn-delete); font-family: monospace; font-size: 0.8rem; padding: 10px;">Error: ${data.detalle || 'No se pudo cargar'}</div>`;
                  }
              }
          })
          .catch(err => {
              console.error("[Explorer] Error cargando directorios:", err);
              if (explorerList) {
                  explorerList.innerHTML = '<div style="color: var(--btn-delete); font-family: monospace; font-size: 0.8rem; padding: 10px;">Error de red al cargar carpetas.</div>';
              }
          });
  }

  // Cablear botones del explorador de carpetas
  const btnBrowseRoms = document.getElementById('btn-browse-roms');
  if (btnBrowseRoms) {
      btnBrowseRoms.addEventListener('click', (e) => {
          e.preventDefault();
          openFolderExplorer(document.getElementById('cfg-roms-path'));
      });
  }
  const btnBrowseWizardRoms = document.getElementById('btn-browse-wizard-roms');
  if (btnBrowseWizardRoms) {
      btnBrowseWizardRoms.addEventListener('click', (e) => {
          e.preventDefault();
          openFolderExplorer(document.getElementById('wizard-roms-path'));
      });
  }
  const explorerSelectBtn = document.getElementById('explorer-select-btn');
  if (explorerSelectBtn) {
      explorerSelectBtn.addEventListener('click', (e) => {
          e.preventDefault();
          if (activeExplorerTargetInput) {
              activeExplorerTargetInput.value = explorerCurrentPath;
              activeExplorerTargetInput.dispatchEvent(new Event('input'));
              activeExplorerTargetInput.dispatchEvent(new Event('change'));
          }
          closeFolderExplorer();
      });
  }
  const explorerCloseBtn = document.getElementById('explorer-close-btn');
  if (explorerCloseBtn) {
      explorerCloseBtn.addEventListener('click', (e) => {
          e.preventDefault();
          closeFolderExplorer();
      });
  }

  selectorCloseBtn.addEventListener('click', hideCustomSelector);

  // Intercept native dropdowns to open custom selectors in Couch Mode
  const couchSelects = [
      { id: 'console-filter', title: 'FILTRAR POR CONSOLA' },
      { id: 'sort-filter', title: 'ORDENAR REPOSITORIO' },
      { id: 'version-select', title: 'SELECCIONAR VERSION' },
      { id: 'audio-select', title: 'DISPOSITIVO DE AUDIO' },
      { id: 'cfg-theme', title: 'TEMA VISUAL' },
      { id: 'cfg-workspace-dual', title: 'WORKSPACE DE JUEGOS (DUAL)' },
      { id: 'cfg-workspace-stream', title: 'WORKSPACE DE TRANSMISION' },
      { id: 'cfg-target-monitor-dual', title: 'MONITOR SECUNDARIO (TV)' },
      { id: 'cfg-host-monitor-dual', title: 'MONITOR PRINCIPAL PC (DUAL)' },
      { id: 'cfg-host-monitor-single', title: 'MONITOR PRINCIPAL PC' },
      { id: 'cfg-host-monitor-stream', title: 'MONITOR PRINCIPAL PC (STREAM)' },
      { id: 'emu-ps1', title: 'EMULADOR PLAYSTATION 1' },
      { id: 'emu-ps2', title: 'EMULADOR PLAYSTATION 2' },
      { id: 'emu-gamecube', title: 'EMULADOR GAMECUBE' },
      { id: 'emu-wii', title: 'EMULADOR WII' },
      { id: 'emu-xbox', title: 'EMULADOR XBOX' },
      { id: 'emu-psp', title: 'EMULADOR PSP' },
      { id: 'cfg-player', title: 'SELECCIONAR JUGADOR' },
      { id: 'cfg-profile', title: 'PERFIL DE CONTROLES' }
  ];

  couchSelects.forEach(item => {
      const el = document.getElementById(item.id);
      if (el) {
          const handler = (e) => {
              if (document.body.classList.contains('couch-mode')) {
                  e.preventDefault();
                  showCustomSelector(el, item.title);
              }
          };
          el.addEventListener('mousedown', handler);
          el.addEventListener('click', handler);
      }
  });

  // Intercept all text inputs to open virtual keyboard in Couch Mode
  document.addEventListener('click', (e) => {
      if (e.target && e.target.tagName === 'INPUT' && e.target.type === 'text') {
          if (document.body.classList.contains('couch-mode') && !isKeyboardActive) {
              e.preventDefault();
              showVirtualKeyboard(e.target);
          }
      }
  });

  // --- TV / Couch Mode Navigation ---

  function focusElement(el) {
      if (focusedElement) {
          focusedElement.classList.remove('focused');
      }
      focusedElement = el;
      if (focusedElement) {
          focusedElement.classList.add('focused');
          focusedElement.focus();
          focusedElement.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
  }

  function navigateSpatial(direction) {
      let focusable;
      const isModalOpen = !modal.classList.contains('hidden');
      const isDownloadsVisible = !downloadsView.classList.contains('hidden');
      const isSettingsVisible = !settingsView.classList.contains('hidden');
      const wizardEl = document.getElementById('setup-wizard');
      const isWizardOpen = wizardEl && !wizardEl.classList.contains('hidden');
      const mappingModal = document.getElementById('controls-mapping-modal');
      const isMappingOpen = mappingModal && !mappingModal.classList.contains('hidden');
      
      if (isExplorerOpen) {
          focusable = Array.from(document.querySelectorAll('#explorer-list button, #explorer-select-btn, #explorer-close-btn'));
      } else if (isConfirmOpen) {
          focusable = Array.from(document.querySelectorAll('#confirm-yes-btn, #confirm-no-btn'));
      } else if (isSelectorOpen) {
          focusable = Array.from(document.querySelectorAll('#selector-options-grid button, #selector-close-btn'));
      } else if (isMappingOpen) {
          focusable = Array.from(document.querySelectorAll('#controls-mapping-modal select, #controls-mapping-modal button'));
      } else if (isWizardOpen) {
          focusable = Array.from(document.querySelectorAll(
              '#setup-wizard .wizard-step:not(.hidden) button:not([disabled]), ' +
              '#setup-wizard .wizard-step:not(.hidden) select, ' +
              '#setup-wizard .wizard-step:not(.hidden) input, ' +
              '#setup-wizard .wizard-footer button:not([disabled])'
          ));
      } else if (isModalOpen) {
          focusable = Array.from(modal.querySelectorAll('.fav-btn, .btn-primary:not(.hidden), .btn-secondary:not(.hidden), .action-btn:not(.hidden), #version-select'));
      } else if (isKeyboardActive) {
          focusable = Array.from(document.querySelectorAll('.key-btn'));
      } else if (isSettingsVisible) {
          // Incluir nav-btns + todos los controles interactivos de settings (incluyendo botones del mapping grid)
          focusable = Array.from(document.querySelectorAll(
              '.nav-btn, #settings-view select, #settings-view input[type="text"], #settings-view input[type="checkbox"], #settings-view button, #mapping-grid button'
          ));
      } else if (isDownloadsVisible) {
          focusable = Array.from(document.querySelectorAll('.nav-btn, #downloads-view button'));
      } else {
          focusable = Array.from(document.querySelectorAll('.nav-btn, .game-card, #search-input, #pagination-controls button:not([disabled]), #sort-filter, #console-filter, #refresh-library-btn:not(.hidden)'));
      }
      
      if (focusable.length === 0) return;
      
      if (!focusedElement || !focusable.includes(focusedElement)) {
          focusElement(focusable[0]);
          return;
      }
      
      const currentRect = focusedElement.getBoundingClientRect();
      const currentCenterX = currentRect.left + currentRect.width / 2;
      const currentCenterY = currentRect.top + currentRect.height / 2;
      
      let bestCandidate = null;
      let bestScore = Infinity;
      
      focusable.forEach((el) => {
          if (el === focusedElement) return;
          const r = el.getBoundingClientRect();
          const cx = r.left + r.width / 2;
          const cy = r.top + r.height / 2;
          
          const dx = cx - currentCenterX;
          const dy = cy - currentCenterY;
          
          let valid = false;
          let score = 0;
          
          if (direction === 'ArrowRight' && dx > 5) {
              valid = true;
              score = Math.abs(dy) * 2.5 + dx;
          } else if (direction === 'ArrowLeft' && dx < -5) {
              valid = true;
              score = Math.abs(dy) * 2.5 + Math.abs(dx);
          } else if (direction === 'ArrowDown' && dy > 5) {
              valid = true;
              score = Math.abs(dx) * 2.5 + dy;
          } else if (direction === 'ArrowUp' && dy < -5) {
              valid = true;
              score = Math.abs(dx) * 2.5 + Math.abs(dy);
          }
          
          if (valid && score < bestScore) {
              bestScore = score;
              bestCandidate = el;
          }
      });
      
      if (bestCandidate) {
          focusElement(bestCandidate);
      }
  }

  // --- Teclado Virtual Retro ---
  const keyboardGrid = document.getElementById('keyboard-grid');
  const virtualKeyboard = document.getElementById('virtual-keyboard');
  const keyboardPreview = document.getElementById('keyboard-preview');

  const keysList = [
      'Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P',
      'A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', 'Ñ',
      'Z', 'X', 'C', 'V', 'B', 'N', 'M', ',', '.', '-',
      '1', '2', '3', '4', '5', '6', '7', '8', '9', '0',
      'ESPACIO', 'DEL', 'LIMPIAR', 'CERRAR'
  ];

  function initVirtualKeyboard() {
      if (!keyboardGrid) return;
      keyboardGrid.innerHTML = '';
      
      keysList.forEach(key => {
          const btn = document.createElement('button');
          btn.className = 'key-btn';
          btn.textContent = key;
          
          if (key === 'ESPACIO') {
              btn.classList.add('extra-wide');
          } else if (key === 'DEL' || key === 'LIMPIAR' || key === 'CERRAR') {
              btn.classList.add('wide');
          }
          
          btn.addEventListener('click', () => handleKeypress(key));
          keyboardGrid.appendChild(btn);
      });
  }

  function handleKeypress(key) {
      if (!activeInputEl) return;
      let val = activeInputEl.value;
      if (key === 'DEL') {
          activeInputEl.value = val.substring(0, val.length - 1);
      } else if (key === 'ESPACIO') {
          activeInputEl.value = val + ' ';
      } else if (key === 'LIMPIAR') {
          activeInputEl.value = '';
      } else if (key === 'CERRAR') {
          hideVirtualKeyboard();
          return;
      } else {
          activeInputEl.value = val + key;
      }
      
      // Update text preview box in real-time
      if (keyboardPreview) {
          keyboardPreview.textContent = activeInputEl.value || '_';
      }
      
      // Trigger input and change events
      activeInputEl.dispatchEvent(new Event('input'));
      activeInputEl.dispatchEvent(new Event('change'));
  }

  function showVirtualKeyboard(inputEl) {
      if (isKeyboardActive) return;
      isKeyboardActive = true;
      activeInputEl = inputEl || searchInput;
      virtualKeyboard.classList.remove('hidden');
      
      // Sync preview initially
      if (keyboardPreview) {
          keyboardPreview.textContent = activeInputEl.value || '_';
      }
      
      initVirtualKeyboard();
      
      // Auto-focus the first key in the keyboard (Q key)
      setTimeout(() => {
          const firstKey = keyboardGrid.querySelector('.key-btn');
          if (firstKey) focusElement(firstKey);
      }, 150);
  }

  function hideVirtualKeyboard() {
      if (!isKeyboardActive) return;
      isKeyboardActive = false;
      virtualKeyboard.classList.add('hidden');
      
      // Restore focus to the input that opened it
      const elToFocus = activeInputEl;
      activeInputEl = null;
      setTimeout(() => {
          if (elToFocus) focusElement(elToFocus);
      }, 150);
  }

  // --- Keyboard Listeners ---
  document.addEventListener('keydown', (e) => {
      if (isGamePlaying) return;
      const key = e.key;
      const isCouchActive = document.body.classList.contains('couch-mode');
      
      if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(key)) {
          if (isCouchActive) {
              e.preventDefault();
              navigateSpatial(key);
          }
      } else if (key === 'Enter') {
          if (isCouchActive && focusedElement) {
              e.preventDefault();
              if (focusedElement.tagName === 'INPUT' && focusedElement.type === 'text') {
                  showVirtualKeyboard(focusedElement);
                  return;
              }
              if (focusedElement.tagName === 'SELECT') {
                  const item = couchSelects.find(x => x.id === focusedElement.id);
                  const title = item ? item.title : 'SELECCIONAR';
                  showCustomSelector(focusedElement, title);
              } else {
                  focusedElement.click();
              }
              // Auto-focus el primer botón disponible del modal si se abrió uno
              setTimeout(() => {
                  if (!modal.classList.contains('hidden')) {
                      const firstModalBtn = modal.querySelector('.btn-primary:not(.hidden), .btn-secondary:not(.hidden)');
                      if (firstModalBtn) focusElement(firstModalBtn);
                  }
              }, 180);
          }
      } else if (key === 'Escape') {
          if (isExplorerOpen) {
              closeFolderExplorer();
              return;
          }
          if (isKeyboardActive) {
              hideVirtualKeyboard();
              return;
          }
          if (isSelectorOpen) {
              hideCustomSelector();
              return;
          }
          if (isConfirmOpen) {
              closeConfirmModal(false);
              return;
          }
          const mappingModalEl = document.getElementById('controls-mapping-modal');
          if (mappingModalEl && !mappingModalEl.classList.contains('hidden')) {
              mappingModalEl.classList.add('hidden');
              const openMappingBtnRef = document.getElementById('open-mapping-btn');
              if (openMappingBtnRef) focusElement(openMappingBtnRef);
              return;
          }
          if (!modal.classList.contains('hidden')) {
              closeModal();
              if (isCouchActive) {
                  setTimeout(() => {
                      const firstCard = document.querySelector('.game-card');
                      if (firstCard) focusElement(firstCard);
                  }, 180);
              }
          }
      }
  });

  // --- Gamepad API Support (Joystick) ---

  function populateProfilesSelect(activeProfile = null) {
      const profileSelect = document.getElementById('cfg-profile');
      if (!profileSelect) return;
      
      const currentVal = activeProfile || profileSelect.value || "gamepad";
      profileSelect.innerHTML = '';
      
      // Opción de Teclado
      const optKb = document.createElement('option');
      optKb.value = 'keyboard';
      optKb.textContent = ' TECLADO (KEYBOARD)';
      profileSelect.appendChild(optKb);
      
      // Obtener mandos conectados
      const gamepads = navigator.getGamepads();
      let gpCount = 0;
      
      Array.from(gamepads).forEach((gp) => {
          if (gp !== null) {
              gpCount++;
              const optGp = document.createElement('option');
              const profileVal = gpCount === 1 ? 'gamepad' : `gamepad${gpCount}`;
              optGp.value = profileVal;
              optGp.textContent = ` MANDO ${gpCount}: ${gp.id.substring(0, 20).toUpperCase()}`;
              profileSelect.appendChild(optGp);
          }
      });
      
      // Agregar mandos genéricos del 1 al 4 si no se poblaron mandos físicos
      if (gpCount < 4) {
          for (let i = gpCount + 1; i <= 4; i++) {
              const optGp = document.createElement('option');
              const profileVal = i === 1 ? 'gamepad' : `gamepad${i}`;
              optGp.value = profileVal;
              optGp.textContent = ` MANDO GENERAL ${i}`;
              profileSelect.appendChild(optGp);
          }
      }
      
      // Restaurar el valor seleccionado
      profileSelect.value = currentVal;
  }

  window.addEventListener("gamepadconnected", (e) => {
      console.log("Gamepad conectado:", e.gamepad.id);
      setCouchMode(true, true);
      populateProfilesSelect();
  });

  window.addEventListener("gamepaddisconnected", (e) => {
      console.log("Gamepad desconectado:", e.gamepad.id);
      const gamepads = navigator.getGamepads();
      const activeGps = Array.from(gamepads).filter(g => g !== null);
      if (activeGps.length === 0) {
          stopGamepadPolling();
      }
      populateProfilesSelect();
  });

  function startGamepadPolling() {
      if (gamepadInterval) return;
      gamepadInterval = setInterval(pollGamepad, 120); // 120ms = ~8fps, suficiente para navegacion sin lag
  }

  function stopGamepadPolling() {
      clearInterval(gamepadInterval);
      gamepadInterval = null;
  }

  function pollGamepad() {
      if (isGamePlaying) return;
      const gamepads = navigator.getGamepads();
      const activeGps = Array.from(gamepads).filter(g => g !== null);
      
      // Mapear botón o eje nativo en caliente si estamos remapeando mando en la UI
      if (currentMappingAction && activeSettings) {
          const profileSelect = document.getElementById('cfg-profile');
          const profileVal = profileSelect ? profileSelect.value : 'gamepad';
          if (profileVal !== 'keyboard') { // Mapeo de control/gamepad
              let mapped = false;
              activeGps.forEach(gp => {
                  if (mapped) return;
                  // Escanear botones
                  gp.buttons.forEach((btn, idx) => {
                      if (btn.pressed && !mapped) {
                          activeSettings.controls[profileVal][currentMappingAction] = `b${idx}`;
                          currentMappingAction = null;
                          mapped = true;
                          renderMappingGrid();
                      }
                  });
                  // Escanear ejes
                  if (!mapped) {
                      gp.axes.forEach((axis, idx) => {
                          if (Math.abs(axis) > 0.65 && !mapped) {
                              activeSettings.controls[profileVal][currentMappingAction] = `a${idx}`;
                              currentMappingAction = null;
                              mapped = true;
                              renderMappingGrid();
                          }
                      });
                  }
              });
              if (mapped) return; // Salir de la ejecución del polling para este tick
          }
      }

      if (activeGps.length === 0) return;
      
      const isCouchActive = document.body.classList.contains('couch-mode');
      if (!isCouchActive) return;

      let dpadUp = false;
      let dpadDown = false;
      let dpadLeft = false;
      let dpadRight = false;
      let btnA = false;
      let btnB = false;

      activeGps.forEach(gp => {
           let up = gp.buttons[12]?.pressed;
           let down = gp.buttons[13]?.pressed;
           let left = gp.buttons[14]?.pressed;
           let right = gp.buttons[15]?.pressed;

           // 1. Joystick analógico izquierdo (ejes 0 y 1)
           const stickX = gp.axes[0] || 0;
           const stickY = gp.axes[1] || 0;
           if (stickY < -0.5) up = true;
           if (stickY > 0.5) down = true;
           if (stickX < -0.5) left = true;
           if (stickX > 0.5) right = true;

           // 2. Mandos genéricos: D-pad mapeado como ejes alternativos (ejes 4/5 o 6/7)
           const altX = gp.axes[4] !== undefined ? gp.axes[4] : (gp.axes[6] !== undefined ? gp.axes[6] : 0);
           const altY = gp.axes[5] !== undefined ? gp.axes[5] : (gp.axes[7] !== undefined ? gp.axes[7] : 0);
           if (altY < -0.5) up = true;
           if (altY > 0.5) down = true;
           if (altX < -0.5) left = true;
           if (altX > 0.5) right = true;

           // 3. Eje 9 (Hat Switch genérico muy común en chips chinos: arriba=-1, derecha=-0.42, abajo=0.14, izquierda=0.71)
           const hat = gp.axes[9] !== undefined ? gp.axes[9] : 0;
           if (hat !== 0) {
               if (hat >= -1.05 && hat <= -0.7) up = true;
               if (hat >= -0.75 && hat <= -0.1) right = true;
               if (hat >= -0.15 && hat <= 0.45) down = true;
               if (hat >= 0.4 && hat <= 1.05) left = true;
           }

           if (up) dpadUp = true;
           if (down) dpadDown = true;
           if (left) dpadLeft = true;
           if (right) dpadRight = true;

           if (gp.buttons[0]?.pressed) btnA = true;
           if (gp.buttons[1]?.pressed) btnB = true;
       });

      // --- Combo Select+Start (buttons 8+9) para salir de Steam/juego ---
      activeGps.forEach(gp => {
          const btnSelect = gp.buttons[8]?.pressed;
          const btnStart  = gp.buttons[9]?.pressed;
          if (btnSelect && btnStart) {
              if (!lastButtonStates.selectStartCombo) {
                  lastButtonStates.selectStartCombo = true;
                  if (isGamePlaying) {
                      // Pedir cierre forzado al backend
                      fetch(`${API_BASE_URL}/cerrar_emulador`, { method: 'POST' })
                          .catch(err => console.error('[Combo] Error cerrando emulador:', err));
                      showToast('Cerrando... volviendo a RetroCloud', 'info');
                  }
              }
          } else {
              lastButtonStates.selectStartCombo = false;
          }
      });

      const now = Date.now();
      const throttle = 200;
      if (!lastButtonStates.lastNavTime) lastButtonStates.lastNavTime = 0;

      // Si estamos esperando input para remapear un control, no navegar con el joystick
      if (!currentMappingAction) {
          if (now - lastButtonStates.lastNavTime > throttle) {
              if (dpadUp) { navigateSpatial('ArrowUp'); lastButtonStates.lastNavTime = now; }
              else if (dpadDown) { navigateSpatial('ArrowDown'); lastButtonStates.lastNavTime = now; }
              else if (dpadLeft) { navigateSpatial('ArrowLeft'); lastButtonStates.lastNavTime = now; }
              else if (dpadRight) { navigateSpatial('ArrowRight'); lastButtonStates.lastNavTime = now; }
          }
      }

      // 2. Button A / Cross (Select)
      if (btnA && !lastButtonStates.btnA) {
          const event = new KeyboardEvent('keydown', { key: 'Enter' });
          document.dispatchEvent(event);
          tryFullscreen();
      }
      lastButtonStates.btnA = btnA;

      // 3. Button B / Circle (Cancel)
      if (btnB && !lastButtonStates.btnB) {
          const event = new KeyboardEvent('keydown', { key: 'Escape' });
          document.dispatchEvent(event);
          tryFullscreen();
      }
      lastButtonStates.btnB = btnB;
  }

  // Event Listeners Nav
  
  navCatalog.addEventListener('click', () => {
      showCatalogView();
      if (document.body.classList.contains('couch-mode')) {
          setTimeout(() => {
              const firstCard = document.querySelector('.game-card');
              if (firstCard) {
                  focusElement(firstCard);
              } else {
                  focusElement(navCatalog);
              }
          }, 150);
      }
  });

  navLocal.addEventListener('click', () => {
      showLocalView();
      if (document.body.classList.contains('couch-mode')) {
          setTimeout(() => {
              const firstCard = document.querySelector('.game-card');
              if (firstCard) {
                  focusElement(firstCard);
              } else {
                  focusElement(navLocal);
              }
          }, 250);
      }
  });

  navFavorites.addEventListener('click', () => {
      showFavoritesView();
      if (document.body.classList.contains('couch-mode')) {
          setTimeout(() => {
              const firstCard = document.querySelector('.game-card');
              if (firstCard) {
                  focusElement(firstCard);
              } else {
                  focusElement(navFavorites);
              }
          }, 150);
      }
  });

  navDownloads.addEventListener('click', () => {
      showDownloadsView();
      if (document.body.classList.contains('couch-mode')) {
          setTimeout(() => {
              const firstBtn = downloadsView.querySelector('button');
              if (firstBtn) {
                  focusElement(firstBtn);
              } else {
                  focusElement(navDownloads);
              }
          }, 250);
      }
  });

  navSettings.addEventListener('click', () => {
      showSettingsView();
      if (document.body.classList.contains('couch-mode')) {
          // Dar tiempo a que se rendericen los elementos de settings
          setTimeout(() => {
              // Intentar enfocar el primer elemento interactivo dentro de settings-view
              const firstSettingsEl = settingsView.querySelector('select, input[type="checkbox"], button');
              if (firstSettingsEl) {
                  focusElement(firstSettingsEl);
              } else {
                  focusElement(navSettings);
              }
          }, 400);
      }
  });

  audioSelect.addEventListener('change', () => {
      const selectedSink = audioSelect.value;
      if (!selectedSink) return;
      
      localStorage.setItem('retro_selected_audio', selectedSink);
      fetch(`${API_BASE_URL}/audio/seleccionar?sink_name=${encodeURIComponent(selectedSink)}`, { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            if (data.estado !== "OK") {
                console.error("[Audio] Error:", data.detalle);
            }
        }).catch(err => console.error("Error de red cambiando audio:", err));
  });

  steamBtn.addEventListener('click', (e) => {
      e.preventDefault();
      showConfirmModal("¿ABRIR STEAM BIG PICTURE?", () => {
          const originalText = steamBtn.textContent;
          steamBtn.textContent = 'INICIANDO...';
          steamBtn.disabled = true;
          isGamePlaying = true;
          stopGamepadPolling();
          
          updateNav(steamBtn);
          viewTitle.textContent = 'EJECUTANDO STEAM...';
          
          fetch(`${API_BASE_URL}/steam/bigpicture`)
            .then(res => res.json())
            .then(data => {
                if (data.estado === 'OK') {
                    steamBtn.textContent = ' EN EJECUCION';
                    
                    setTimeout(() => {
                        let checkSteamInterval = setInterval(() => {
                            fetch(`${API_BASE_URL}/estado_emulador`)
                              .then(res => res.json())
                              .then(dataCheck => {
                                  if (!dataCheck.activo) {
                                      clearInterval(checkSteamInterval);
                                      isGamePlaying = false;
                                      isGamePaused = false;
                                      const banner = document.getElementById('game-paused-banner');
                                      if (banner) banner.classList.add('hidden');
                                      startGamepadPolling();
                                      steamBtn.textContent = originalText;
                                      steamBtn.disabled = false;
                                      
                                      // Re-enfocar el navegador para restaurar el gamepad
                                      fetch(`${API_BASE_URL}/foco`).catch(err => console.error(err));
                                      
                                      setTimeout(() => {
                                          focusElement(steamBtn);
                                      }, 500);
                                  }
                              }).catch(err => {
                                  console.error(err);
                              });
                        }, 2000);
                    }, 8000);
                } else {
                    showToast("Error al iniciar Steam: " + data.detalle, "error");
                    steamBtn.textContent = originalText;
                    steamBtn.disabled = false;
                    isGamePlaying = false;
                    startGamepadPolling();
                    focusElement(steamBtn);
                }
            }).catch(err => {
                console.error("Error de red iniciando Steam:", err);
                steamBtn.textContent = originalText;
                steamBtn.disabled = false;
                isGamePlaying = false;
                startGamepadPolling();
                focusElement(steamBtn);
            });
      }, () => {
          focusElement(steamBtn);
      });
  });

  const profileSelect = document.getElementById('cfg-profile');
  const playerSelect = document.getElementById('cfg-player');
  
  if (playerSelect) {
      playerSelect.addEventListener('change', () => {
          if (profileSelect && activeSettings && activeSettings.controls) {
              const playerKey = playerSelect.value;
              const assignedProfile = activeSettings.controls[playerKey + "_profile"] || (playerKey === 'p1' ? 'gamepad' : (playerKey === 'p2' ? 'gamepad2' : (playerKey === 'p3' ? 'gamepad3' : 'gamepad4')));
              profileSelect.value = assignedProfile;
          }
          renderMappingGrid();
      });
  }

  if (profileSelect) {
      profileSelect.addEventListener('change', () => {
          if (playerSelect && activeSettings && activeSettings.controls) {
              const playerKey = playerSelect.value;
              activeSettings.controls[playerKey + "_profile"] = profileSelect.value;
          }
          renderMappingGrid();
      });
  }

  // --- Dedicated Controls Mapping Modal Wiring ---
  const openMappingBtn = document.getElementById('open-mapping-btn');
  const closeMappingBtn = document.getElementById('close-mapping-btn');
  const controlsMappingModal = document.getElementById('controls-mapping-modal');
  // Obtener el overlay INTERNO del modal de controles (no el global del game-modal)
  const controlsMappingOverlay = controlsMappingModal ? controlsMappingModal.querySelector('.modal-overlay') : null;

  if (openMappingBtn && controlsMappingModal) {
      openMappingBtn.addEventListener('click', (e) => {
          e.preventDefault();
          e.stopPropagation();
          controlsMappingModal.classList.remove('hidden');
          
          // Poblar la lista de perfiles disponibles (incluyendo mandos físicos)
          populateProfilesSelect();
          
          // Sincronizar el perfil actual del jugador seleccionado
          if (playerSelect && profileSelect && activeSettings && activeSettings.controls) {
              const playerKey = playerSelect.value || 'p1';
              const assignedProfile = activeSettings.controls[playerKey + "_profile"] || (playerKey === 'p1' ? 'gamepad' : (playerKey === 'p2' ? 'gamepad2' : (playerKey === 'p3' ? 'gamepad3' : 'gamepad4')));
              profileSelect.value = assignedProfile;
          }
          
          renderMappingGrid();
          setTimeout(() => {
              const grid = document.getElementById('mapping-grid');
              const firstBtn = grid ? grid.querySelector('button') : null;
              if (firstBtn) {
                  focusElement(firstBtn);
              } else if (closeMappingBtn) {
                  focusElement(closeMappingBtn);
              }
          }, 50);
      });
  }

  // Cerrar el modal de controles si se hace click en su overlay interno
  if (controlsMappingOverlay) {
      controlsMappingOverlay.addEventListener('click', (e) => {
          e.stopPropagation();
          controlsMappingModal.classList.add('hidden');
          if (openMappingBtn) focusElement(openMappingBtn);
      });
  }

  if (closeMappingBtn && controlsMappingModal) {
      closeMappingBtn.addEventListener('click', (e) => {
          e.preventDefault();
          
          if (activeSettings) {
              const originalText = closeMappingBtn.textContent;
              closeMappingBtn.textContent = 'GUARDANDO CONTROLES...';
              closeMappingBtn.disabled = true;
              
              // Sincronizar el perfil actual en activeSettings
              const pSel = document.getElementById('cfg-profile');
              if (pSel) {
                  activeSettings.controls.profile = pSel.value;
              }
              
              fetch(`${API_BASE_URL}/ajustes`, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify(activeSettings)
              })
              .then(res => res.json())
              .then(data => {
                  closeMappingBtn.disabled = false;
                  closeMappingBtn.textContent = originalText;
                  if (data.estado === 'OK') {
                      showToast("¡Controles guardados con éxito!", "success");
                      controlsMappingModal.classList.add('hidden');
                      if (openMappingBtn) {
                          focusElement(openMappingBtn);
                      }
                  } else {
                      showToast("Error al guardar controles: " + data.detalle, "error");
                  }
              })
              .catch(err => {
                  closeMappingBtn.disabled = false;
                  closeMappingBtn.textContent = originalText;
                  console.error("Error al guardar controles:", err);
                  showToast("Error de conexión al guardar controles.", "error");
              });
          } else {
              controlsMappingModal.classList.add('hidden');
              if (openMappingBtn) {
                  focusElement(openMappingBtn);
              }
          }
      });
  }

  const saveSettingsBtn = document.getElementById('save-settings-btn');
  if (saveSettingsBtn) {
      saveSettingsBtn.addEventListener('click', (e) => {
          e.preventDefault();
          if (!activeSettings) return;
          const originalText = saveSettingsBtn.textContent;
          
          if (document.getElementById('cfg-crt')) activeSettings.video.crt_shader = document.getElementById('cfg-crt').checked;
          if (document.getElementById('cfg-bilinear')) activeSettings.video.bilinear_filtering = document.getElementById('cfg-bilinear').checked;
          if (document.getElementById('cfg-fps')) activeSettings.video.show_fps = document.getElementById('cfg-fps').checked;
          if (document.getElementById('cfg-aspect')) activeSettings.video.aspect_ratio = document.getElementById('cfg-aspect').value;
          
          const mode = window._settingsScreenMode || 'single';
          if (mode === 'stream') {
              activeSettings.versatility.host_monitor = (document.getElementById('cfg-host-monitor-stream') || {}).value || 'DP-1';
              activeSettings.versatility.target_monitor = 'TV-STREAM';
              activeSettings.versatility.target_workspace = (document.getElementById('cfg-workspace-stream') || {}).value || '10';
          } else if (mode === 'dual') {
              const hostMon = (document.getElementById('cfg-host-monitor-dual') || {}).value;
              const targetMon = (document.getElementById('cfg-target-monitor-dual') || {}).value;
              if (hostMon && targetMon && hostMon === targetMon) {
                  showToast("Para usar el modo de pantalla dual, la pantalla de TV y la de PC deben ser diferentes. Si usás la misma pantalla, seleccioná 'Una sola pantalla'.", "warning", 6000);
                  saveSettingsBtn.textContent = originalText;
                  saveSettingsBtn.disabled = false;
                  saveSettingsBtn.style.background = '';
                  return;
              }
              activeSettings.versatility.host_monitor = hostMon || 'DP-1';
              activeSettings.versatility.target_monitor = targetMon || 'TV-STREAM';
              activeSettings.versatility.target_workspace = (document.getElementById('cfg-workspace-dual') || {}).value || '10';
          } else {
              const mon = (document.getElementById('cfg-host-monitor-single') || {}).value || 'DP-1';
              activeSettings.versatility.host_monitor = mon;
              activeSettings.versatility.target_monitor = mon;
              activeSettings.versatility.target_workspace = '1';
          }
          
          // Sincronizar inputs ocultos por retrocompatibilidad
          const hiddenWorkspace = document.getElementById('cfg-workspace');
          const hiddenTarget = document.getElementById('cfg-target-monitor');
          const hiddenHost = document.getElementById('cfg-host-monitor');
          if (hiddenWorkspace) hiddenWorkspace.value = activeSettings.versatility.target_workspace;
          if (hiddenTarget) hiddenTarget.value = activeSettings.versatility.target_monitor;
          if (hiddenHost) hiddenHost.value = activeSettings.versatility.host_monitor;
          
          activeSettings.controls.profile = document.getElementById('cfg-profile').value;
          
          // Guardar emuladores
          if (!activeSettings.emulators) activeSettings.emulators = {};
          if (document.getElementById('emu-ps1')) activeSettings.emulators.ps1 = document.getElementById('emu-ps1').value;
          if (document.getElementById('emu-ps2')) activeSettings.emulators.ps2 = document.getElementById('emu-ps2').value;
          if (document.getElementById('emu-gamecube')) activeSettings.emulators.gamecube = document.getElementById('emu-gamecube').value;
          if (document.getElementById('emu-wii')) activeSettings.emulators.wii = document.getElementById('emu-wii').value;
          if (document.getElementById('emu-xbox')) activeSettings.emulators.xbox = document.getElementById('emu-xbox').value;
          if (document.getElementById('emu-psp')) activeSettings.emulators.psp = document.getElementById('emu-psp').value;

          // Guardar y aplicar tema
          const themeSelector = document.getElementById('cfg-theme');
          if (themeSelector) {
              const newTheme = themeSelector.value;
              activeSettings.theme = newTheme;
              localStorage.setItem('retro_theme', newTheme);
              document.body.setAttribute('data-theme', newTheme);
          }
          
          // Guardar el modo de pantalla elegido EXPLICITAMENTE
          activeSettings.screen_mode = mode;
          
          // Guardar ruta de ROMs
          if (document.getElementById('cfg-roms-path')) {
              activeSettings.roms_path = document.getElementById('cfg-roms-path').value.trim() || '';
          }
          
          saveSettingsBtn.textContent = 'GUARDANDO AJUSTES...';
          saveSettingsBtn.disabled = true;
          saveSettingsBtn.style.background = 'var(--btn-secondary)';
          
          fetch(`${API_BASE_URL}/ajustes`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(activeSettings)
          })
          .then(res => res.json())
          .then(data => {
              if (data.estado === 'OK') {
                  saveSettingsBtn.textContent = ' ¡GUARDADO CON EXITO!';
                  saveSettingsBtn.style.background = '#2ecc71';
                  saveSettingsBtn.style.color = '#fff';
                  
                  setTimeout(() => {
                      saveSettingsBtn.textContent = originalText;
                      saveSettingsBtn.style.background = '';
                      saveSettingsBtn.style.color = '';
                      saveSettingsBtn.disabled = false;
                  }, 2000);
              } else {
                  showToast("Error al guardar: " + data.detalle, "error");
                  saveSettingsBtn.textContent = originalText;
                  saveSettingsBtn.style.background = '';
                  saveSettingsBtn.style.color = '';
                  saveSettingsBtn.disabled = false;
              }
          })
          .catch(err => {
              console.error("Error guardando ajustes:", err);
              saveSettingsBtn.textContent = originalText;
              saveSettingsBtn.style.background = '';
              saveSettingsBtn.style.color = '';
              saveSettingsBtn.disabled = false;
          });
      });
  }

  const rebuildCatalogBtn = document.getElementById('rebuild-catalog-btn');
  if (rebuildCatalogBtn) {
      rebuildCatalogBtn.addEventListener('click', () => {
          showConfirmation("¿Seguro que deseas reconstruir el catálogo global? Esto descargará y procesará de nuevo la lista de juegos de Minerva (puede tardar unos minutos en segundo plano).", () => {
              const originalText = rebuildCatalogBtn.textContent;
              rebuildCatalogBtn.textContent = 'SOLICITANDO RECONSTRUCCION...';
              rebuildCatalogBtn.disabled = true;
              
              fetch(`${API_BASE_URL}/catalogo/rebuild`, { method: 'POST' })
                  .then(res => res.json())
                  .then(data => {
                      if (data.estado === 'OK') {
                          showToast("Reconstrucción del catálogo iniciada en segundo plano.", "success");
                          rebuildCatalogBtn.textContent = ' PROCESANDO EN FONDO';
                          rebuildCatalogBtn.style.background = '#2ecc71';
                          rebuildCatalogBtn.style.color = '#fff';
                          
                          setTimeout(() => {
                              rebuildCatalogBtn.textContent = originalText;
                              rebuildCatalogBtn.style.background = '';
                              rebuildCatalogBtn.style.color = '';
                              rebuildCatalogBtn.disabled = false;
                          }, 5000);
                      } else {
                          showToast("Error al reconstruir catálogo: " + data.detalle, "error");
                          rebuildCatalogBtn.textContent = originalText;
                          rebuildCatalogBtn.disabled = false;
                      }
                  })
                  .catch(err => {
                      console.error("Error reconstruyendo catálogo:", err);
                      showToast("Error de red al reconstruir catálogo.", "error");
                      rebuildCatalogBtn.textContent = originalText;
                      rebuildCatalogBtn.disabled = false;
                  });
          });
      });
  }

  const runWizardBtn = document.getElementById('run-wizard-btn');
  if (runWizardBtn) {
      runWizardBtn.addEventListener('click', (e) => {
          e.preventDefault();
          startSetupWizard();
      });
  }

  if (refreshLibraryBtn) {
      refreshLibraryBtn.addEventListener('click', () => {
          const originalText = refreshLibraryBtn.textContent;
          refreshLibraryBtn.textContent = '↻ ESCANEANDO...';
          refreshLibraryBtn.disabled = true;
          refreshLibraryBtn.style.background = '#dcdde1';
          refreshLibraryBtn.style.borderColor = '#7f8fa6';
          
          fetch(`${API_BASE_URL}/libreria`)
              .then(res => res.json())
              .then(data => {
                  localGames = data;
                  applyFilters();
                  
                  // Volver al estado normal con feedback exitoso
                  refreshLibraryBtn.textContent = ' ¡ACTUALIZADO!';
                  refreshLibraryBtn.style.background = '#2ecc71';
                  refreshLibraryBtn.style.borderColor = '#27ae60';
                  
                  setTimeout(() => {
                      refreshLibraryBtn.textContent = originalText;
                      refreshLibraryBtn.disabled = false;
                      refreshLibraryBtn.style.background = '';
                      refreshLibraryBtn.style.borderColor = '';
                  }, 1500);
              }).catch(err => {
                  console.error("Error al refrescar la biblioteca:", err);
                  refreshLibraryBtn.textContent = ' ERROR';
                  refreshLibraryBtn.style.background = '#e84118';
                  refreshLibraryBtn.style.borderColor = '#c23616';
                  
                  setTimeout(() => {
                      refreshLibraryBtn.textContent = originalText;
                      refreshLibraryBtn.disabled = false;
                      refreshLibraryBtn.style.background = '';
                      refreshLibraryBtn.style.borderColor = '';
                  }, 2000);
              });
      });
  }

  if (navTv) {
      navTv.addEventListener('click', () => {
          const isCouch = !document.body.classList.contains('couch-mode');
          setCouchMode(isCouch, true);
      });
  }

  modalOverlay.addEventListener('click', (e) => {
      // Solo cerrar el game-modal, no afectar otros modales
      const modal = document.getElementById('game-modal');
      if (modal && !modal.classList.contains('hidden')) {
          closeModal();
      }
  });

  // --- Botón Salir de DUCKY GAME HUB ---
  const navExit = document.getElementById('nav-exit');
  if (navExit) {
      navExit.addEventListener('click', () => {
          showConfirmModal('¿SALIR A ESCRITORIO?', () => {
              fetch(`${API_BASE_URL}/salir`, { method: 'POST' })
                  .catch(() => {});
              setTimeout(() => {
                  window.close();
                  // Fallback si window.close() no funciona (navegadores lo bloquean)
                  document.body.innerHTML = `<div style="display:flex;flex-direction:column;justify-content:center;align-items:center;height:100vh;background:#06080c;font-family:'Press Start 2P',cursive;color:#00a8ff;font-size:1rem;text-align:center;gap:20px;"><div>CERRANDO DUCKY GAME HUB...</div><span style="font-size:0.6rem;color:#aaa;">Podes cerrar esta ventana.</span></div>`;
              }, 500);
          }, () => {});
      });
  }

  // --- APLICAR TEMA INICIAL ---
  const savedTheme = localStorage.getItem('retro_theme') || 'neon';
  document.body.setAttribute('data-theme', savedTheme);




  // Función global para el toggle de pantalla en ajustes (llamada desde onclick en HTML)
  window.setSettingsScreenMode = function(mode) {
      window._settingsScreenMode = mode;
      const panelSingle = document.getElementById('cfg-panel-single');
      const panelDual   = document.getElementById('cfg-panel-dual');
      const panelStream = document.getElementById('cfg-panel-stream');
      const btnSingle   = document.getElementById('cfg-screen-mode-single');
      const btnDual     = document.getElementById('cfg-screen-mode-dual');
      const btnStream   = document.getElementById('cfg-screen-mode-stream');
      if (!panelSingle || !panelDual || !panelStream) return;

      panelSingle.style.display = 'none';
      panelDual.style.display   = 'none';
      panelStream.style.display = 'none';
      
      if (btnSingle) { btnSingle.style.background = ''; btnSingle.style.borderColor = ''; btnSingle.style.color = ''; btnSingle.className = 'btn-secondary'; }
      if (btnDual)   { btnDual.style.background = ''; btnDual.style.borderColor = ''; btnDual.style.color = ''; btnDual.className = 'btn-secondary'; }
      if (btnStream) { btnStream.style.background = ''; btnStream.style.borderColor = ''; btnStream.style.color = ''; btnStream.className = 'btn-secondary'; }

      if (mode === 'dual') {
          panelDual.style.display   = 'flex';
          if (btnDual)   { btnDual.style.background = 'var(--accent-cyan)'; btnDual.style.borderColor = 'var(--accent-cyan)'; btnDual.style.color = 'black'; btnDual.className = 'btn-primary'; }
      } else if (mode === 'stream') {
          panelStream.style.display = 'flex';
          if (btnStream) { btnStream.style.background = 'var(--accent-cyan)'; btnStream.style.borderColor = 'var(--accent-cyan)'; btnStream.style.color = 'black'; btnStream.className = 'btn-primary'; }
      } else {
          panelSingle.style.display = 'flex';
          if (btnSingle) { btnSingle.style.background = 'var(--accent-gold)'; btnSingle.style.borderColor = 'var(--accent-gold)'; btnSingle.style.color = 'black'; btnSingle.className = 'btn-primary'; }
      }
  };


  // Función global para el toggle de pantalla en el wizard (llamada desde onclick en HTML)
  window.setWizardScreenMode = function(mode) {
      window._wizardScreenMode = mode;
      const panelSingle = document.getElementById('wizard-panel-single');
      const panelDual   = document.getElementById('wizard-panel-dual');
      const panelStream = document.getElementById('wizard-panel-stream');
      const btnSingle   = document.getElementById('wizard-screen-mode-single');
      const btnDual     = document.getElementById('wizard-screen-mode-dual');
      const btnStream   = document.getElementById('wizard-screen-mode-stream');
      if (!panelSingle || !panelDual || !panelStream) return;

      panelSingle.style.display = 'none';
      panelDual.style.display   = 'none';
      panelStream.style.display = 'none';
      
      if (btnSingle) { btnSingle.style.background = ''; btnSingle.style.borderColor = ''; btnSingle.style.color = ''; btnSingle.className = 'btn-secondary'; }
      if (btnDual)   { btnDual.style.background = ''; btnDual.style.borderColor = ''; btnDual.style.color = ''; btnDual.className = 'btn-secondary'; }
      if (btnStream) { btnStream.style.background = ''; btnStream.style.borderColor = ''; btnStream.style.color = ''; btnStream.className = 'btn-secondary'; }

      if (mode === 'dual') {
          panelDual.style.display   = 'flex';
          if (btnDual)   { btnDual.style.background = 'var(--accent-cyan)'; btnDual.style.borderColor = 'var(--accent-cyan)'; btnDual.style.color = 'black'; btnDual.className = 'btn-primary'; }
      } else if (mode === 'stream') {
          panelStream.style.display = 'flex';
          if (btnStream) { btnStream.style.background = 'var(--accent-cyan)'; btnStream.style.borderColor = 'var(--accent-cyan)'; btnStream.style.color = 'black'; btnStream.className = 'btn-primary'; }
      } else {
          panelSingle.style.display = 'flex';
          if (btnSingle) { btnSingle.style.background = 'var(--accent-gold)'; btnSingle.style.borderColor = 'var(--accent-gold)'; btnSingle.style.color = 'black'; btnSingle.className = 'btn-primary'; }
      }
  };


  let wizardCurrentStep = 1;
  const wizardTotalSteps = 5;
  const setupWizardModal = document.getElementById('setup-wizard');
  const wizardBtnPrev = document.getElementById('wizard-btn-prev');
  const wizardBtnNext = document.getElementById('wizard-btn-next');
  const btnTestSsh = document.getElementById('btn-test-ssh');
  const sshTestStatus = document.getElementById('ssh-test-status');

  function startSetupWizard() {
      if (!setupWizardModal) return;
      setupWizardModal.classList.remove('hidden');
      wizardCurrentStep = 1;
      showWizardStep(1);
      
      // Inicializar modo de pantalla: por defecto una sola pantalla
      window._wizardScreenMode = 'single';
      setTimeout(() => setWizardScreenMode('single'), 80); // pequeño delay para que el DOM esté listo
      
      // Cargar monitores y audio
      cargarDatosWizard();


      // Interceptar los selects del wizard para Couch Mode
      const wizardSelects = [
          { id: 'wizard-host-monitor', title: 'MONITOR PRINCIPAL PC' },
          { id: 'wizard-target-monitor', title: 'MONITOR DE STREAMING (TV)' },
          { id: 'wizard-workspace', title: 'WORKSPACE DE JUEGOS' },
          { id: 'wizard-audio-sink', title: 'DISPOSITIVO DE AUDIO' }
      ];

      wizardSelects.forEach(item => {
          const el = document.getElementById(item.id);
          if (el) {
              el.addEventListener('mousedown', (e) => {
                  if (document.body.classList.contains('couch-mode')) {
                      e.preventDefault();
                      showCustomSelector(el, item.title);
                  }
              });
              el.addEventListener('click', (e) => {
                  if (document.body.classList.contains('couch-mode')) {
                      e.preventDefault();
                      showCustomSelector(el, item.title);
                  }
              });
          }
      });

      // Registrar también los selects del panel dual
      const wizardDualSelects = [
          { id: 'wizard-host-monitor-dual', title: 'MONITOR DE LA PC' },
          { id: 'wizard-target-monitor-dual', title: 'PANTALLA DE LA TV' },
          { id: 'wizard-workspace-dual', title: 'WORKSPACE DE JUEGOS' },
      ];
      wizardDualSelects.forEach(item => {
          const el = document.getElementById(item.id);
          if (el) {
              el.addEventListener('mousedown', (e) => {
                  if (document.body.classList.contains('couch-mode')) {
                      e.preventDefault();
                      showCustomSelector(el, item.title);
                  }
              });
              el.addEventListener('click', (e) => {
                  if (document.body.classList.contains('couch-mode')) {
                      e.preventDefault();
                      showCustomSelector(el, item.title);
                  }
              });
          }
      });
      
      // Capturar inputs para pruebas de control
      const testKeyDetector = document.getElementById('wizard-key-detected');
      const gamepadDeviceInfo = document.getElementById('wizard-gamepad-device-info');
      
      if (gamepadDeviceInfo) {
          if (socket && socket.readyState === WebSocket.OPEN) {
              gamepadDeviceInfo.textContent = "Buscando mandos conectados a través del Daemon local...";
              gamepadDeviceInfo.style.color = 'var(--text-secondary)';
          } else {
              gamepadDeviceInfo.textContent = "Teclado activo. Mando inactivo en Daemon local.";
              gamepadDeviceInfo.style.color = 'var(--text-secondary)';
          }
      }
      
      const keyListener = (e) => {
          if (!setupWizardModal.classList.contains('hidden') && wizardCurrentStep === 5 && testKeyDetector) {
              testKeyDetector.textContent = `TECLADO: "${e.key.toUpperCase()}"`;
              testKeyDetector.style.color = 'var(--accent-cyan)';
          }
      };
      window.addEventListener('keydown', keyListener);
  }

  function showWizardStep(step) {
      document.querySelectorAll('.wizard-step').forEach(el => el.classList.add('hidden'));
      const activeEl = document.getElementById(`wizard-step-${step}`);
      if (activeEl) activeEl.classList.remove('hidden');
      
      // Indicadores de pasos (dots)
      document.querySelectorAll('.step-dot').forEach((dot, idx) => {
          dot.className = 'step-dot';
          if (idx + 1 === step) dot.classList.add('active');
          else if (idx + 1 < step) dot.classList.add('completed');
      });
      
      if (wizardBtnPrev) wizardBtnPrev.style.visibility = step === 1 ? 'hidden' : 'visible';
      if (wizardBtnNext) {
          if (step === wizardTotalSteps) {
              wizardBtnNext.textContent = ' FINALIZAR';
              wizardBtnNext.style.background = '#4cd137';
              wizardBtnNext.style.borderColor = '#4cd137';
          } else {
              wizardBtnNext.textContent = 'SIGUIENTE ►';
              wizardBtnNext.style.background = 'var(--accent-gold)';
              wizardBtnNext.style.borderColor = 'var(--accent-gold)';
          }
      }

      // Auto-enfocar el primer elemento interactivo del paso actual o el botón "Siguiente"
      setTimeout(() => {
          const stepFocusable = Array.from(document.querySelectorAll(
              `#wizard-step-${step} select:not([type='hidden']), #wizard-step-${step} button:not([disabled]), #wizard-step-${step} input:not([type='hidden'])`
          ));
          if (stepFocusable.length > 0) {
              focusElement(stepFocusable[0]);
          } else if (wizardBtnNext && !wizardBtnNext.disabled) {
              focusElement(wizardBtnNext);
          }
      }, 50);
  }

  if (wizardBtnPrev) {
      wizardBtnPrev.addEventListener('click', () => {
          if (wizardCurrentStep > 1) {
              wizardCurrentStep--;
              showWizardStep(wizardCurrentStep);
          }
      });
  }

  if (wizardBtnNext) {
      wizardBtnNext.addEventListener('click', () => {
          if (wizardCurrentStep < wizardTotalSteps) {
              wizardCurrentStep++;
              showWizardStep(wizardCurrentStep);
          } else {
              // Guardar ajustes finales y completar wizard
              guardarAjustesWizard();
          }
      });
  }

  if (btnTestSsh) {
      btnTestSsh.addEventListener('click', () => {
          btnTestSsh.disabled = true;
          btnTestSsh.textContent = 'COMPROBANDO...';
          sshTestStatus.textContent = 'ESTADO: PING SSH...';
          sshTestStatus.style.color = '';
          
          fetch(`${API_BASE_URL}/ssh/test`)
            .then(res => res.json())
            .then(data => {
                btnTestSsh.disabled = false;
                btnTestSsh.textContent = 'PROBAR CONEXION SSH';
                if (data.estado === 'OK') {
                    sshTestStatus.textContent = 'ESTADO:  CONEXION EXITOSA';
                    sshTestStatus.style.color = '#4cd137';
                    showToast("¡Conexión SSH comprobada con éxito!", "success");
                } else {
                    sshTestStatus.textContent = 'ESTADO:  FALLIDO';
                    sshTestStatus.style.color = '#e84118';
                    showToast(`Error SSH: ${data.detalle || 'Host inalcanzable'}`, "error");
                }
            })
            .catch(err => {
                btnTestSsh.disabled = false;
                btnTestSsh.textContent = 'PROBAR CONEXION SSH';
                sshTestStatus.textContent = 'ESTADO:  ERROR DE API';
                sshTestStatus.style.color = '#e84118';
                showToast("No se pudo contactar a la API de RetroCloud.", "error");
            });
      });
  }

  function cargarDatosWizard() {
      // Sincronizar ajustes cargados del SSH y ROMs
      if (activeSettings) {
          const romsPathInput = document.getElementById('wizard-roms-path');
          if (romsPathInput && activeSettings.roms_path) {
              romsPathInput.value = activeSettings.roms_path;
          }
          const sshInfoCode = document.getElementById('wizard-ssh-info');
          if (sshInfoCode && activeSettings.host_ip && activeSettings.host_user) {
              sshInfoCode.innerHTML = `HOST_IP=${activeSettings.host_ip}  # Detectado automáticamente<br>HOST_USER=${activeSettings.host_user}  # Detectado automáticamente (whoami)`;
          }
      }

      // Cargar pantallas
      fetch(`${API_BASE_URL}/pantallas`)
        .then(res => res.json())
        .then(data => {
            const hSel  = document.getElementById('wizard-host-monitor');
            const tSel  = document.getElementById('wizard-target-monitor'); // hidden input in single mode
            const hDual = document.getElementById('wizard-host-monitor-dual');
            const tDual = document.getElementById('wizard-target-monitor-dual');
            const hStream = document.getElementById('wizard-host-monitor-stream');
            const monitores = data.pantallas || [];
            [hSel, hDual, tDual, hStream].forEach(sel => {
                if (!sel || sel.tagName !== 'SELECT') return;
                sel.innerHTML = '';
                monitores.forEach(p => {
                    const opt = document.createElement('option');
                    opt.value = opt.textContent = p;
                    if (sel === hSel && p === 'DP-1') opt.selected = true;
                    if (sel === hDual && p === 'DP-1') opt.selected = true;
                    if (sel === hStream && p === 'DP-1') opt.selected = true;
                    if (sel === tDual && p === 'TV-STREAM') opt.selected = true;
                    sel.appendChild(opt);
                });
            });
            // Sincronizar hidden target con el primero disponible para modo single
            if (tSel && tSel.tagName === 'INPUT' && monitores.length > 0) {
                tSel.value = monitores.find(p => p === 'TV-STREAM') || monitores[0];
            }
        }).catch(err => console.error("Error cargando pantallas en wizard:", err));
        
      // Cargar audio sinks
      fetch(`${API_BASE_URL}/audio/dispositivos`)
        .then(res => res.json())
        .then(data => {
            const aSel = document.getElementById('wizard-audio-sink');
            if (aSel && data.estado === 'OK') {
                aSel.innerHTML = '';
                data.dispositivos.forEach(d => {
                    const opt = document.createElement('option');
                    opt.value = d.name;
                    opt.textContent = d.description;
                    aSel.appendChild(opt);
                });
            }
        }).catch(err => console.error("Error cargando audio sinks en wizard:", err));
  }

  function guardarAjustesWizard() {
      if (!activeSettings) return;

      // Determinar si el usuario eligió modo single, dual o stream
      const mode = window._wizardScreenMode || 'single';

      if (mode === 'stream') {
          activeSettings.versatility.host_monitor   = (document.getElementById('wizard-host-monitor-stream') || {}).value || 'DP-1';
          activeSettings.versatility.target_monitor = 'TV-STREAM';
          activeSettings.versatility.target_workspace = (document.getElementById('wizard-workspace-stream') || {}).value || '10';
      } else if (mode === 'dual') {
          const hostMon = (document.getElementById('wizard-host-monitor-dual') || {}).value;
          const targetMon = (document.getElementById('wizard-target-monitor-dual') || {}).value;
          if (hostMon && targetMon && hostMon === targetMon) {
              showToast("Para usar el modo de pantalla dual, la pantalla de TV y la de PC deben ser diferentes. Si usás la misma pantalla, seleccioná 'Una sola pantalla'.", "warning", 6000);
              return;
          }
          activeSettings.versatility.host_monitor   = hostMon || 'DP-1';
          activeSettings.versatility.target_monitor = targetMon || 'TV-STREAM';
          activeSettings.versatility.target_workspace = (document.getElementById('wizard-workspace-dual') || {}).value || '10';
      } else {
          // Modo simple: juegos en la misma pantalla que el host
          const mon = (document.getElementById('wizard-host-monitor') || {}).value || 'DP-1';
          activeSettings.versatility.host_monitor   = mon;
          activeSettings.versatility.target_monitor = mon;
          activeSettings.versatility.target_workspace = '1';
      }

      activeSettings.audio.selected_sink = (document.getElementById('wizard-audio-sink') || {}).value || '';
      activeSettings.roms_path = (document.getElementById('wizard-roms-path') || {}).value.trim() || '';
      activeSettings.first_run = false;
      
      showToast("Guardando ajustes iniciales...", "info");
      
      fetch(`${API_BASE_URL}/ajustes/wizard-complete`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(activeSettings)
      })
      .then(res => res.json())
      .then(data => {
          if (data.estado === 'OK') {
              showToast("¡Configuración guardada! Bienvenido a RetroCloud.", "success");
              if (setupWizardModal) setupWizardModal.classList.add('hidden');
              // Sincronizar el panel principal con los valores guardados
              let loadedMode = 'single';
              if (activeSettings.versatility.target_monitor === 'TV-STREAM' && activeSettings.versatility.target_workspace === '10') {
                  loadedMode = 'stream';
              } else if (activeSettings.versatility.target_workspace !== '1' || activeSettings.versatility.target_monitor !== activeSettings.versatility.host_monitor) {
                  loadedMode = 'dual';
              }
              if (typeof window.setSettingsScreenMode === 'function') {
                  window.setSettingsScreenMode(loadedMode);
              }
              if (document.getElementById('cfg-workspace-dual')) document.getElementById('cfg-workspace-dual').value = activeSettings.versatility.target_workspace;
              if (document.getElementById('cfg-target-monitor-dual')) document.getElementById('cfg-target-monitor-dual').value = activeSettings.versatility.target_monitor;
              if (document.getElementById('cfg-host-monitor-dual')) document.getElementById('cfg-host-monitor-dual').value = activeSettings.versatility.host_monitor;
              if (document.getElementById('cfg-host-monitor-single')) document.getElementById('cfg-host-monitor-single').value = activeSettings.versatility.host_monitor;
              if (document.getElementById('cfg-host-monitor-stream')) document.getElementById('cfg-host-monitor-stream').value = activeSettings.versatility.host_monitor;
              
              // Sincronizar inputs ocultos por retrocompatibilidad
              const cfgWs = document.getElementById('cfg-workspace');
              const cfgTm = document.getElementById('cfg-target-monitor');
              const cfgHm = document.getElementById('cfg-host-monitor');
              if (cfgWs) cfgWs.value = activeSettings.versatility.target_workspace;
              if (cfgTm) cfgTm.value = activeSettings.versatility.target_monitor;
              if (cfgHm) cfgHm.value = activeSettings.versatility.host_monitor;
          } else {
              showToast(`Error al guardar configuración: ${data.detalle}`, "error");
          }
      })
      .catch(err => {
          console.error("Error finalizando wizard:", err);
          showToast("Error de conexión al finalizar el asistente.", "error");
      });
  }

  // --- Check Active Downloads Badge ---
  function checkActiveDownloadsBadge() {
    fetch(`${API_BASE_URL}/descargas`)
      .then(res => res.json())
      .then(data => {
        const active = Object.values(data).some(d => d.progress < 100 && d.status !== 'Error');
        const badgeId = 'downloads-badge';
        let badge = document.getElementById(badgeId);
        
        if (active) {
            if (!badge) {
                badge = document.createElement('span');
                badge.id = badgeId;
                badge.style = 'background: #e84118; width: 8px; height: 8px; border-radius: 50%; display: inline-block; margin-left: 10px; box-shadow: 0 0 8px #e84118; animation: pulse-download 1.5s infinite; vertical-align: middle;';
                navDownloads.appendChild(badge);
            }
        } else {
            if (badge) badge.remove();
        }
      }).catch(err => console.error("Error checking downloads badge:", err));
  }

  // toggleGamePause fue eliminado por completo

  checkActiveDownloadsBadge();
  setInterval(checkActiveDownloadsBadge, 5000);

});
