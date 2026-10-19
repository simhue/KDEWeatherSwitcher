# AutoWeatherTheme

Changes KDE's color scheme to Breeze Light during clear daylight and Breeze Dark
at night or when cloud cover reaches 80%. It switches back to light below 60%
cloud cover, retaining its previous choice between the thresholds. Checks run
every five minutes, so sunrise/sunset changes can take up to five minutes.

Requires Python 3 and KDE's `plasma-apply-colorscheme`; no Python packages or API
key are needed. Weather and sunrise/sunset data come from
[Open-Meteo](https://open-meteo.com/en/docs) (attribution: Open-Meteo, CC BY 4.0).
The coordinates for Aachen, Germany are sent to this service.

KDE provides automatic day/night themes in Plasma 6.5
([KDE announcement](https://blogs.kde.org/2025/08/02/this-week-in-plasma-day/night-theme-switching/)).
This script handles both daylight and weather itself to avoid competing
controllers. Disable KDE's automatic light/dark theme switching before using it.
It applies color schemes rather than global themes, preserving your choice of
icons, desktop layout, and wallpaper. Applications must support following KDE's
color scheme for their appearance to change.

## Try it

Run from a terminal in your KDE desktop session:

```sh
python3 auto_weather_theme.py --config auto-weather-theme.ini --once --dry-run
python3 auto_weather_theme.py --config auto-weather-theme.ini --once
```

Edit `auto-weather-theme.ini` to change coordinates, color schemes, cloud
thresholds, or polling interval. List installed schemes with
`plasma-apply-colorscheme --list-schemes`.

## Install as a user service

Run these commands from this directory, as your desktop user:

```sh
mkdir -p ~/.local/bin ~/.config/systemd/user
install -m 755 auto_weather_theme.py ~/.local/bin/auto_weather_theme.py
install -m 644 auto-weather-theme.ini ~/.config/auto-weather-theme.ini
install -m 644 auto-weather-theme.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now auto-weather-theme.service
```

The service starts with the graphical session and stops when it ends. Do not run
it as root or as a system service: it needs your desktop session's D-Bus and
display environment. If needed, run this inside a KDE terminal and restart it:

```sh
systemctl --user import-environment DISPLAY WAYLAND_DISPLAY DBUS_SESSION_BUS_ADDRESS
systemctl --user restart auto-weather-theme.service
```

After editing `~/.config/auto-weather-theme.ini`, restart the service. View logs
with `journalctl --user -u auto-weather-theme.service -f`. Stop and disable it
with `systemctl --user disable --now auto-weather-theme.service`; the last
selected color scheme remains applied.

When a weather request fails, the running service uses its last daylight
forecast for up to three UTC calendar days. Cloud readings older than one hour
are ignored, so daytime defaults to light. Without a usable forecast (including
an offline first start), it leaves the current scheme alone and retries next
interval. Forecasts are held in memory, not persisted across service restarts.
Locations where the provider returns missing sunrise/sunset times are not
supported.
