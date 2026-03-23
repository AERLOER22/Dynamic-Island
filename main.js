const { app, BrowserWindow, screen, ipcMain, globalShortcut } = require('electron');
const fs = require('fs');
const path = require('path');
const { spawn, exec } = require('child_process');

function createWindow() {
  // Узнаем размер экрана пользователя
  const primaryDisplay = screen.getPrimaryDisplay();
  const { width } = primaryDisplay.workAreaSize;

  // Создаем прозрачное окно без рамок
  const win = new BrowserWindow({
    width: 600, // Увеличиваем ширину окна под большой плеер
    height: 250, // Увеличиваем высоту
    x: (width - 600) / 2, // Центрируем по горизонтали
    y: 0, // Приклеиваем к верхнему краю
    transparent: true, // Прозрачный фон окна
    frame: false, // Отключаем стандартные рамки Windows (крестик, свернуть)
    alwaysOnTop: true, // Всегда поверх всех окон
    skipTaskbar: true, // Не показываем в панели задач
    resizable: false, // Запрещаем растягивать
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    }
  });

  win.loadFile('index.html');

  // Жестко закрепляем окно поверх ВСЕХ окон, включая полноэкранные игры и браузер
  win.setAlwaysOnTop(true, 'screen-saver');
  win.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });

  // По умолчанию прозрачная часть окна пропускает клики сквозь себя (эффект прозрачного стекла)
  win.setIgnoreMouseEvents(true, { forward: true });

  // Остров сам скажет, когда нужно ловить клики (при наведении мышки на сам островок)
  ipcMain.on('set-ignore-mouse-events', (event, ignore) => {
    const webContents = event.sender;
    const window = BrowserWindow.fromWebContents(webContents);
    window.setIgnoreMouseEvents(ignore, { forward: true });
  });

  // Глобальная горячая клавиша для возврата и скрытия острова (Ctrl + Shift + I)
  globalShortcut.register('CommandOrControl+Shift+I', () => {
    win.webContents.send('toggle-island');
  });

  // Глобальная горячая клавиша для переключения стиля iPhone 13 / 16 (Ctrl + Shift + Alt + F1)
  globalShortcut.register('CommandOrControl+Shift+Alt+F1', () => {
    win.webContents.send('toggle-style');
  });

  // Глобальная горячая клавиша для имитации подключения Bluetooth (Ctrl + Shift + B)
  globalShortcut.register('CommandOrControl+Shift+B', () => {
    win.webContents.send('show-bluetooth');
  });

  win.webContents.once('did-finish-load', () => {
    startMediaListener(win);
  });

  // Принимаем клики по кнопкам плеера и передаем их в Windows
  ipcMain.on('media-play-pause', () => sendMediaCmd('playpause'));
  ipcMain.on('media-next', () => sendMediaCmd('next'));
  ipcMain.on('media-prev', () => sendMediaCmd('prev'));
}

// Вспомогательная функция для красивого формата времени (например, 1:24)
function formatTime(seconds) {
  if (isNaN(seconds) || seconds < 0) return "0:00";
  const min = Math.floor(seconds / 60);
  const sec = seconds % 60;
  return `${min}:${sec < 10 ? '0' : ''}${sec}`;
}

app.whenReady().then(() => {
  createWindow();

  // Настройка автозапуска при включении ПК
  app.setLoginItemSettings({
    openAtLogin: true,
    path: app.getPath('exe') // Путь к нашему собранному .exe
  });
});

// Скрываем в трей или предотвращаем закрытие, если закрыли все окна
app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit(); });

// --- Блок связи с настоящим Windows-плеером через Python --- //

// Отправка команд (переключение, пауза)
function sendMediaCmd(cmd) {
  // Используем встроенный язык Windows (PowerShell), чтобы не зависеть от Питона для кнопок
  const psCmd = `
    [Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager, Windows.Media, ContentType=WindowsRuntime] | Out-Null
    $req = [Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager]::RequestAsync()
    while ($req.Status -eq 'Started') { Start-Sleep -Milliseconds 10 }
    $manager = $req.GetResults()
    $session = $manager.GetCurrentSession()
    if ($null -ne $session) {
        $action = "${cmd}"
        if ($action -eq "playpause") { $req2 = $session.TryTogglePlayPauseAsync() }
        elseif ($action -eq "next") { $req2 = $session.TrySkipNextAsync() }
        elseif ($action -eq "prev") { $req2 = $session.TrySkipPreviousAsync() }
        
        if ($null -ne $req2) { while ($req2.Status -eq 'Started') { Start-Sleep -Milliseconds 10 } }
    }
  `;
  const psEncoded = Buffer.from(psCmd, 'utf16le').toString('base64');
  exec(`powershell.exe -NoProfile -NonInteractive -EncodedCommand ${psEncoded}`);
}

// Умная функция, которая находит наши новые exe-шники как при тесте, так и в собранном приложении
function getExePath(name) {
  return app.isPackaged 
    ? path.join(process.resourcesPath, 'python-bin', name) 
    : path.join(__dirname, 'python-bin', name);
}

// Чтение трека, времени и обложки каждую секунду
function startMediaListener(win) {
  const ps = spawn(getExePath('media.exe'), [], { windowsHide: true });
  ps.stdout.setEncoding('utf8');

  // --- ДОБАВЛЯЕМ ОТЛАДКУ ОШИБОК PYTHON ---
  ps.stderr.setEncoding('utf8');
  ps.stderr.on('data', (err) => {
    console.error("Python Error:", err);
  });

  ps.on('error', (err) => {
    console.error("Failed to start Python:", err);
    win.webContents.send('update-media', { title: 'Python не найден!', artist: 'Установи Python и добавь в PATH', playing: false, progress: 0, elapsed: '0:00', remaining: '-0:00', albumArt: 'none' });
  });

  ps.on('close', (code) => {
    if (code !== 0) {
      win.webContents.send('update-media', { title: 'Ошибка скрипта', artist: `Введи: pip install winsdk`, playing: false, progress: 0, elapsed: '0:00', remaining: '-0:00', albumArt: 'none' });
    }
  });

  let dataBuffer = '';
  ps.stdout.on('data', (chunk) => {
    dataBuffer += chunk;
    let lines = dataBuffer.split('\n');
    dataBuffer = lines.pop(); // сохраняем неполную строку

    for (let line of lines) {
      line = line.trim();
      if (line.startsWith('{') && line.endsWith('}')) {
        try {
          const data = JSON.parse(line);
          
          if (!data.playing && !data.title) {
            win.webContents.send('update-media', { title: 'Нет музыки', artist: 'Ожидание...', playing: false, progress: 0, elapsed: '0:00', remaining: '-0:00', albumArt: 'none' });
            continue;
          }

          let albumArt = null;
          if (data.image === 'none') albumArt = 'none';
          else if (data.image === 'same') albumArt = 'same';
          else if (data.image) albumArt = 'data:image/png;base64,' + data.image;

          const progress = data.endTime > 0 ? (data.position / data.endTime) * 100 : 0;

          win.webContents.send('update-media', {
            title: data.title || 'Неизвестно',
            artist: data.artist || '',
            playing: data.playing,
            progress: progress,
            elapsed: formatTime(data.position),
            remaining: '-' + formatTime(data.endTime - data.position),
            albumArt: albumArt
          });
        } catch (e) { console.log("JSON Error:", e); }
      }
    }
  });

  // --- ЗАПУСКАЕМ ВТОРОЙ СКРИПТ ДЛЯ БЛЮТУЗА ---
  const btPs = spawn(getExePath('bluetooth.exe'), [], { windowsHide: true });
  btPs.stdout.setEncoding('utf8');

  let btBuffer = '';
  btPs.stdout.on('data', (chunk) => {
    btBuffer += chunk;
    let lines = btBuffer.split('\n');
    btBuffer = lines.pop(); 

    for (let line of lines) {
      line = line.trim();
      if (line.startsWith('{') && line.endsWith('}')) {
        try {
          const data = JSON.parse(line);
          if (data.type === 'bluetooth') {
            win.webContents.send('show-bluetooth-real', data);
          }
        } catch (e) {}
      }
    }
  });

  // --- ЗАПУСКАЕМ СКРИПТ ДЛЯ ПОЛНОЭКРАННОГО РЕЖИМА ---
  const fsPs = spawn(getExePath('fullscreen.exe'), [], { windowsHide: true });
  fsPs.stdout.setEncoding('utf8');

  let fsBuffer = '';
  fsPs.stdout.on('data', (chunk) => {
    fsBuffer += chunk;
    let lines = fsBuffer.split('\n');
    fsBuffer = lines.pop(); 

    for (let line of lines) {
      line = line.trim();
      if (line.startsWith('{') && line.endsWith('}')) {
        try {
          const data = JSON.parse(line);
          if (data.type === 'fullscreen') win.webContents.send('update-fullscreen', data);
        } catch (e) {}
      }
    }
  });

  // --- ТЕСТ ГРОМКОСТИ НА ГОРЯЧИХ КЛАВИШАХ ---
  let testVolume = 50;
  globalShortcut.register('CommandOrControl+Shift+Up', () => {
    testVolume = Math.min(100, testVolume + 2); // Прибавляем по 2% для очень плавной анимации
    win.webContents.send('update-volume', { volume: testVolume, muted: testVolume === 0 });
  });
  globalShortcut.register('CommandOrControl+Shift+Down', () => {
    testVolume = Math.max(0, testVolume - 2); // Убавляем по 2%
    win.webContents.send('update-volume', { volume: testVolume, muted: testVolume === 0 });
  });

  app.on('before-quit', () => { 
    try { ps.kill(); } catch (e) {}
    try { btPs.kill(); } catch (e) {}
    try { fsPs.kill(); } catch (e) {}
  });
}