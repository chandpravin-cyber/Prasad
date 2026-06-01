# Install Prasad Menu as an iPhone app

The site is now a Progressive Web App (PWA). After install it launches full-screen with its own home-screen icon, works offline, and looks like a native app.

## Quick install (any iPhone)

1. On your Mac, open Terminal and run:
   ```
   cd ~/Documents/Claude/Projects/Prasad
   python3 server.py
   ```
   The terminal will show two URLs — note the **Wi-Fi** one, e.g. `http://192.168.1.42:8080/`.

2. On your iPhone (same Wi-Fi as the Mac), open **Safari** (not Chrome — Add to Home Screen only works in Safari) and go to:
   ```
   http://YOUR-MAC-IP:8080/
   ```

3. Wait a few seconds for the page to load. A small floating card will appear at the bottom telling you to tap **Share → Add to Home Screen**.

4. Tap the **Share** button (square with arrow up, bottom toolbar) → scroll down → **Add to Home Screen** → **Add**.

5. Done. The blue bowl icon appears on your home screen. Tap it and the app launches full-screen — no Safari URL bar, no tabs, just your menu planner.

## Make it work without your Mac running

The app caches everything (HTML + CSVs + icons) the first time it loads, so once installed it works offline. You can put your Mac to sleep, walk away from Wi-Fi, and the app still opens and the menu still works.

**What stops working offline:** the **Save Shopping List** PDF button. That needs `server.py` running because PDFs are generated server-side. Everything else — menu selection, shopping list, unit toggle, people count — works fully offline.

## Install on multiple phones

Repeat steps 2–4 on each phone while they're on your Wi-Fi. Each phone keeps its own copy after install.

## To put it permanently online (so anyone can install from anywhere)

Push the folder to GitHub and turn on GitHub Pages (we walked through this earlier). Then your install URL becomes `https://chandpravin-cyber.github.io/Prasad/` — no Mac needed.

## Updating the app

After you edit any file (CSVs, HTML, icons), bump the version in `sw.js`:

```js
const CACHE_VERSION = 'prasad-v4';  // change number, e.g. v3 -> v4
```

Then re-visit the site once in Safari (without launching from home screen) — the service worker fetches the new version. Or simpler: tell users to long-press the home-screen icon → Remove → re-install.

## Troubleshooting

- **Share menu doesn't show "Add to Home Screen":** you're not in Safari. Open the page in Safari specifically.
- **Icon is generic gray:** Safari sometimes caches the old icon. Remove the app and re-add.
- **App opens with Safari URL bar:** check that the `<meta name="apple-mobile-web-app-capable" content="yes">` line is in the HTML (it is in `prasad_planner_liquid.html`).
- **Service worker not registering:** PWA requires HTTPS or `localhost`. Local Wi-Fi IP works on iOS because Safari treats LAN as trusted, but if it fails, the cache won't build — fall back to manual `python3 server.py` running for online use only.
