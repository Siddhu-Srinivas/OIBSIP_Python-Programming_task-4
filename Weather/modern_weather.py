# -*- coding: utf-8 -*-
"""
WeatherScope Pro - Modern Weather Dashboard (v9.1)
A sleek, interactive weather application with animated UI, dynamic theming,
real-time visualizations, and interactive maps.

This improved version (v9.1) features:
- Live data from OpenWeatherMap API
- Dynamic gradient backgrounds that change with the weather
- Visual "Meter" widgets for current details (Humidity, Wind, etc.)
- "Feels Like" temperature, Sunrise, and Sunset times
- Live, local-time clock in the header
- Dedicated "Hourly" tab with 24-hour graph
- 5-Day Forecast tab with visual cards
- Improved forecast data processing (calculates daily min/max)
- Map markers
- Scrollable content tabs
- Professional "Blue" UI/UX with improved fonts, colors, and layout
- Refactored UI update logic for better maintanence
- UPDATED: Scrollbars on "Current" and "5-Day" tabs are now always visible for clarity.
"""

import threading
import tkinter as tk
from tkinter import messagebox
from datetime import datetime, date, timedelta
from collections import Counter
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.widgets import Meter  # Import the Meter widget
from ttkbootstrap.scrolled import ScrolledFrame # Import for scrollable tabs
import tkintermapview
import requests
import colorsys
import time
import math
try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
    # mplcursors provides simple tooltips on matplotlib plots
    try:
        import mplcursors
        MPLCURSORS_AVAILABLE = True
    except Exception:
        MPLCURSORS_AVAILABLE = False
except Exception:
    MATPLOTLIB_AVAILABLE = False
    MPLCURSORS_AVAILABLE = False

# --- Configuration ---

# ! IMPORTANT: Replace "YOUR_API_KEY_HERE" with your actual OpenWeatherMap API key
# You can get a free one from https://openweathermap.org/api
API_KEY = "6f0f9af0779da1b1566b0ef931f2f61b" 

# Check if the user has replaced the placeholder API key
if API_KEY == "YOUR_API_KEY_HERE":
    print("ERROR: Please replace 'YOUR_API_KEY_HERE' with your OpenWeatherMap API key.")
    # We'll allow the app to run so the user can see the UI,
    # but API calls will fail until they add their key.
    
CURRENT_URL = "http://api.openweathermap.org/data/2.5/weather?q={city}&appid={key}&units=metric"
FORECAST_URL = "http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={key}&units=metric"
CONFIG_CITY_FILE = "last_city.txt"

# Simple in-memory cache for API responses: {city: (timestamp_seconds, data_package)}
CACHE = {}
CACHE_TTL = 300  # seconds

# Weather Icons with Unicode characters
WEATHER_ICONS = {
    "Clear": "☀️",
    "Clouds": "☁️",
    "Rain": "🌧️",
    "Drizzle": "🌦️",
    "Thunderstorm": "⛈️",
    "Snow": "❄️",
    "Mist": "🌫️",
    "Smoke": "🌫️",
    "Haze": "🌁",
    "Dust": "🌪️",
    "Fog": "🌁",
    "Sand": "🏜️",
    "Ash": "🌋",
    "Squall": "🌬️",
    "Tornado": "🌪️",
    "Default": "❓"
}

# Modern UI Theme Configuration (Locked to Light)
THEMES = {
    "light": {
        "dynamic_bg": {
            "Clear": ("#FFF3E0", "#FFE0B2"),
            "Clouds": ("#E8EAF6", "#C5CAE9"),
            "Rain": ("#E3F2FD", "#BBDEFB"),
            "Snow": ("#FAFAFA", "#F5F5F5"),
            "Thunderstorm": ("#EDE7F6", "#D1C4E9"),
            "Default": ("#F5F5F5", "#E0E0E0")
        },
        "gradient_fg": "#000000",
        "gradient_fg_muted": "#424242"
    },
    "dark": { # Kept for GradientFrame fallback, but not used by theme
        "dynamic_bg": {
            "Clear": ("#FFF3E0", "#FFE0B2"),
            "Clouds": ("#E8EAF6", "#C5CAE9"),
            "Rain": ("#E3F2FD", "#BBDEFB"),
            "Snow": ("#FAFAFA", "#F5F5F5"),
            "Thunderstorm": ("#EDE7F6", "#D1C4E9"),
            "Default": ("#F5F5F5", "#E0E0E0")
        },
        "gradient_fg": "#000000",
        "gradient_fg_muted": "#424242"
    }
}

# --- UI Constants / Palette (centralized for consistent design)
PALETTE = {
    'accent': '#0d6efd',      # primary accent (NEW: professional blue)
    'accent_soft': '#cfe2ff',  # NEW: light blue
    'muted': '#6b7280',
    'card_bg': '#ffffff',
    'glass': '#ffffffcc'
}

# Default font used across the app to improve typographic consistency
DEFAULT_FONT = ("Segoe UI", 11)

# --- Custom Widgets ---

class GradientFrame(tk.Frame):
    """
    A custom Frame widget that draws a vertical gradient background.
    """
    def __init__(self, parent, color1, color2, **kwargs):
        super().__init__(parent, **kwargs)
        self.color1 = color1
        self.color2 = color2
        self.canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0)
        self.canvas.pack(fill=BOTH, expand=YES)
        
        self.bind("<Configure>", self._on_resize)
        self._draw_gradient()

    def _on_resize(self, event):
        """Redraw gradient when the frame is resized."""
        self._draw_gradient()

    def _draw_gradient(self):
        """Draws the vertical gradient."""
        self.canvas.delete("gradient")
        width = self.winfo_width()
        height = self.winfo_height()

        if width < 2 or height < 2:
            return

        # Calculate gradient colors
        r1, g1, b1 = self.winfo_rgb(self.color1)
        r2, g2, b2 = self.winfo_rgb(self.color2)
        
        r_ratio = (r2 - r1) / height
        g_ratio = (g2 - g1) / height
        b_ratio = (b2 - b1) / height

        for i in range(height):
            nr = int(r1 + (r_ratio * i))
            ng = int(g1 + (g_ratio * i))
            nb = int(b1 + (b_ratio * i))
            
            # Clamp values to 0-65535 range
            nr = max(0, min(nr, 65535))
            ng = max(0, min(ng, 65535))
            nb = max(0, min(nb, 65535))

            color = f'#{nr:04x}{ng:04x}{nb:04x}'
            self.canvas.create_line(0, i, width, i, fill=color, tags="gradient")

    def update_gradient(self, color1, color2):
        """Updates the gradient colors and redraws."""
        self.color1 = color1
        self.color2 = color2
        self._draw_gradient()

class ForecastCard(ttk.Frame):
    """
    A custom Frame widget to display a single day's forecast.
    """
    def __init__(self, parent, **kwargs):
        super().__init__(parent, padding=10, **kwargs)
        self.configure(style='Card.TFrame') # Use a custom style if available

        self.day_lbl = ttk.Label(self, text="Day", style="ForecastDay.TLabel")
        self.day_lbl.pack(pady=(0, 5))

        self.icon_lbl = ttk.Label(self, text="❓", style="ForecastIcon.TLabel")
        self.icon_lbl.pack(pady=5)

        self.temp_lbl = ttk.Label(self, text="--° / --°", style="ForecastTemp.TLabel")
        self.temp_lbl.pack(pady=5)
    
    def update_info(self, day, icon_char, temp_max, temp_min):
        """Update the forecast card with new data."""
        self.day_lbl.configure(text=day)
        self.icon_lbl.configure(text=icon_char)
        self.temp_lbl.configure(text=f"{temp_max:.0f}° / {temp_min:.0f}°")


# --- Main Application ---

class ModernWeatherDashboard(ttk.Window):
    """Modern Weather Dashboard using ttkbootstrap for enhanced visuals."""
    
    def __init__(self):
        # Lock theme to 'light' ('cosmo')
        self.theme_mode = "light"
        self.theme_name = "cosmo"
        
        super().__init__(themename=self.theme_name)
        
        self.title("WeatherScope Pro")
        self.geometry("1100x750") # Increased size for new features
        self.minsize(900, 650)
        
        # State variables
        self.location_var = tk.StringVar(value=self._load_preference(CONFIG_CITY_FILE, "London"))
        self.weather_data = None
        self.loading = False
        self.current_marker = None
        self.forecast_cards = []
        # Simple timezone offset (seconds) for charts; updated when data arrives
        self._tz_offset = 0
        # Last known numeric temp value used for smooth animations
        self._last_temp_value = None
        # Simple per-instance cache reference (module-level CACHE used)
        self._cache = CACHE
        # Label for the live clock
        self.clock_lbl = None
        
        # Setup UI
        self._setup_styles()
        self._create_layout()
        
        # Load initial weather data
        self.after(100, self.search_weather)
        
        # Start the live clock
        self.after(1000, self._update_clock)
        
    def _load_preference(self, filename, default):
        """Load user preference from file."""
        try:
            with open(filename, 'r') as f:
                return f.read().strip()
        except FileNotFoundError:
            return default
            
    def _save_preference(self, filename, value):
        """Save user preference to file."""
        try:
            with open(filename, 'w') as f:
                f.write(value)
        except Exception as e:
            print(f"Could not save preference to {filename}: {e}")
            
    def _setup_styles(self):
        """Configure modern UI styles."""
        style = self.style
        # Theme is locked to light
        theme_colors = THEMES[self.theme_mode]

        # General base font — using DEFAULT_FONT for consistent typography
        style.configure('.', font=DEFAULT_FONT)

        # Header styling with accent color for a cleaner brand presence
        style.configure("Header.TLabel", font=(DEFAULT_FONT[0], 20, "bold"), foreground=PALETTE['accent'])

        # Accent button style and hover variant (REMOVED, using bootstyle)
        
        # Search Entry
        style.configure("Search.TEntry", font=(DEFAULT_FONT[0], 13))

        # --- Styles for Gradient Card ---
        fg = theme_colors["gradient_fg"]
        fg_muted = theme_colors["gradient_fg_muted"]

        # Card background placeholder; actual gradient is drawn by GradientFrame
        style.configure("Gradient.TFrame", background=PALETTE['card_bg'])
        style.configure("Location.TLabel", font=(DEFAULT_FONT[0], 28, "bold"), foreground=fg)
        style.configure("Icon.TLabel", font=(DEFAULT_FONT[0], 48), foreground=fg)
        style.configure("Temp.TLabel", font=(DEFAULT_FONT[0], 62, "bold"), foreground=fg)
        style.configure("Condition.TLabel", font=(DEFAULT_FONT[0], 14), foreground=fg)
        style.configure("Detail.TLabel", font=(DEFAULT_FONT[0], 12), foreground=fg)
        # Muted text used in footers and small hints
        style.configure("Muted.TLabel", font=(DEFAULT_FONT[0], 9), foreground=fg_muted)

        # --- Styles for Forecast Cards ---
        style.configure("Card.TFrame", relief=SOLID, borderwidth=1, bordercolor="#EAEAEA", background="#FCFCFC")
        style.configure("CardHover.TFrame", relief=SOLID, borderwidth=1, bordercolor=PALETTE['accent'], background=PALETTE['card_bg'])
        style.configure("ForecastDay.TLabel", font=(DEFAULT_FONT[0], 12, "bold"))
        style.configure("ForecastIcon.TLabel", font=(DEFAULT_FONT[0], 24))
        style.configure("ForecastTemp.TLabel", font=(DEFAULT_FONT[0], 11))

        # --- Styles for Meter Subtext ---
        style.configure("Meter.TLabel", font=(DEFAULT_FONT[0], 10, "bold"))
        
        # --- NEW: Style for Notebook Tabs ---
        style.configure("TNotebook.Tab", font=(DEFAULT_FONT[0], 11, "bold"), padding=[12, 6])
            
    def _create_layout(self):
        """Create the main dashboard layout."""
        # Main container with padding
        container = ttk.Frame(self, padding=20)
        container.pack(fill=BOTH, expand=YES)
        
        # Header with logo and theme toggle
        self._create_header(container)
        
        # Search section
        self._create_search_section(container)
        
        # --- 24-Hour Mini-Graph REMOVED ---

        # Content area
        content = ttk.Notebook(container)
        content.pack(fill=BOTH, expand=YES, pady=(20, 0))

        # Weather tabs
        self.current_tab_frame = ttk.Frame(content, padding=0)
        self.hourly_tab_frame = ttk.Frame(content, padding=20) # NEW Hourly Tab
        self.forecast_tab_frame = ttk.Frame(content, padding=0) 
        self.map_tab = ttk.Frame(content, padding=0) 

        content.add(self.current_tab_frame, text="🏠 Current")
        content.add(self.hourly_tab_frame, text="🕒 Hourly") # NEW
        content.add(self.forecast_tab_frame, text="🗓️ 5-Day Forecast")
        content.add(self.map_tab, text="🗺️ Map")

        # Setup tab contents
        self._setup_current_tab()
        self._setup_hourly_tab() # NEW
        self._setup_forecast_tab()
        self._setup_map_tab()
        # Status bar (accessibility & small hints) — shows subtle messages and hover hints
        status_frame = ttk.Frame(container)
        status_frame.pack(fill=X, pady=(10, 0))
        self.status_lbl = ttk.Label(status_frame, text='Ready', style='Muted.TLabel')
        self.status_lbl.pack(side=LEFT)

        # Create loading overlay (a semi-transparent top-level used when fetching data)
        self._create_loading_overlay()

        # Keyboard accessibility: Ctrl+F focusses the search box
        self.bind_all('<Control-f>', lambda e: self.search_entry.focus_set())
        
    def _create_header(self, parent):
        """Create modern header with logo."""
        header = ttk.Frame(parent)
        header.pack(fill=X, pady=(0, 10))
        
        logo = ttk.Label(header, text="🌤 WeatherScope Pro", style="Header.TLabel")
        logo.pack(side=LEFT)
        
        # --- NEW: Live Clock ---
        self.clock_lbl = ttk.Label(header, text="--:--:-- --", style="Header.TLabel", font=(DEFAULT_FONT[0], 18, "normal"))
        self.clock_lbl.pack(side=RIGHT, padx=(10, 0))
        # --- END NEW ---
        
        # Removed theme toggle and demo buttons
        
    def _create_search_section(self, parent):
        """Create modern search bar with effects."""
        search = ttk.Frame(parent)
        search.pack(fill=X, pady=(0, 10))
        
        self.search_entry = ttk.Entry(search,
                                      textvariable=self.location_var,
                                      style="Search.TEntry")
        self.search_entry.pack(side=LEFT, fill=X, expand=YES, padx=(0, 10), ipady=4)
        self.search_entry.bind("<Return>", lambda e: self.search_weather())
        # Accessibility: show hint in status when focusing search
        self.search_entry.bind('<FocusIn>', lambda e: self.status_lbl.configure(text='Type a city and press Enter to search'))
        self.search_entry.bind('<FocusOut>', lambda e: self.status_lbl.configure(text='Ready'))
        
        self.search_btn = ttk.Button(search,
                                     text="Search",
                                     style="primary.TButton", # NEW: Use bootstyle
                                     command=self.search_weather)
        self.search_btn.pack(side=LEFT, ipady=4)
        # Hover/active affordance for the search button
        self.search_btn.bind('<Enter>', lambda e: (self.search_btn.configure(cursor='hand2'), self.status_lbl.configure(text='Search for the city')))
        self.search_btn.bind('<Leave>', lambda e: (self.search_btn.configure(cursor=''), self.status_lbl.configure(text='Ready')))
        
    def _setup_current_tab(self):
        """Set up the current weather tab with a dynamic gradient card."""
        
        # NEW: Add ScrolledFrame
        # --- MODIFIED: Set autohide=False to make scrollbar always visible ---
        scroll_frame = ScrolledFrame(self.current_tab_frame, autohide=False)
        scroll_frame.pack(fill=BOTH, expand=YES)
        
        # Main weather card (placed inside the scrollable container)
        colors = THEMES[self.theme_mode]["dynamic_bg"]["Default"]
        self.gradient_card = GradientFrame(scroll_frame.container, colors[0], colors[1])
        self.gradient_card.pack(fill=BOTH, expand=YES)
        
        # We need an inner frame on top of the canvas to hold widgets
        card = ttk.Frame(self.gradient_card.canvas, style="Gradient.TFrame")
        card.pack(fill=BOTH, expand=YES, padx=30, pady=30)

        # Current location
        self.location_lbl = ttk.Label(card, text="Loading...", style="Location.TLabel")
        self.location_lbl.pack(fill=X)

        # Weather info container
        info = ttk.Frame(card, style="Gradient.TFrame")
        info.pack(fill=BOTH, expand=YES, pady=20)
        info.grid_columnconfigure(1, weight=1)

        # --- Left side - Icon and Temperature ---
        left = ttk.Frame(info, style="Gradient.TFrame")
        left.grid(row=0, column=0, padx=(0, 40), sticky="n")

        self.icon_lbl = ttk.Label(left, text=WEATHER_ICONS["Default"], style="Icon.TLabel")
        self.icon_lbl.pack(pady=(10, 0))

        self.temp_lbl = ttk.Label(left, text="--°C", style="Temp.TLabel")
        self.temp_lbl.pack()

        self.condition_lbl = ttk.Label(left, text="Unknown", style="Condition.TLabel")
        self.condition_lbl.pack()

        # --- Right side - NEW Meter Details ---
        right = ttk.Frame(info, style="Gradient.TFrame")
        right.grid(row=0, column=1, sticky="nsew", pady=(20, 0))
        right.grid_columnconfigure((0, 1), weight=1)
        right.grid_rowconfigure((0, 1), weight=1)

        # Feels Like Meter
        self.feels_like_meter = Meter(right,
                                      metersize=120,
                                      padding=5,
                                      amounttotal=50,
                                      amountused=0,
                                      textright="°C",
                                      subtext="Feels Like",
                                      textfont="-size 20 -weight bold",
                                      subtextfont="-size 10",
                                      bootstyle="info")
        self.feels_like_meter.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # Humidity Meter
        self.humidity_meter = Meter(right,
                                      metersize=120,
                                      padding=5,
                                      amounttotal=100,
                                      amountused=0,
                                      textright="%",
                                      subtext="Humidity",
                                      textfont="-size 20 -weight bold",
                                      subtextfont="-size 10",
                                      bootstyle="success")
        self.humidity_meter.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        # Wind Meter
        self.wind_meter = Meter(right,
                                  metersize=120,
                                  padding=5,
                                  amounttotal=30, # Max m/s (approx 100 km/h)
                                  amountused=0,
                                  textright="m/s",
                                  subtext="Wind",
                                  textfont="-size 20 -weight bold",
                                  subtextfont="-size 10",
                                  bootstyle="warning")
        self.wind_meter.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        # Pressure Meter
        self.pressure_meter = Meter(right,
                                      metersize=120,
                                      padding=5,
                                      amounttotal=1050, # Range 950-1050
                                      amountused=950,
                                      metertype="semi",
                                      textright="hPa",
                                      subtext="Pressure",
                                      textfont="-size 20 -weight bold",
                                      subtextfont="-size 10",
                                      bootstyle="danger")
        self.pressure_meter.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")

        # --- Sunrise / Sunset ---
        sun_frame = ttk.Frame(card, style="Gradient.TFrame")
        sun_frame.pack(fill=X, pady=10)
        
        self.sunrise_lbl = ttk.Label(sun_frame, text="Sunrise: --:--", style="Detail.TLabel")
        self.sunrise_lbl.pack(side=LEFT, expand=YES)
        
        self.sunset_lbl = ttk.Label(sun_frame, text="Sunset: --:--", style="Detail.TLabel")
        self.sunset_lbl.pack(side=RIGHT, expand=YES)

        # Last updated
        # --- FIX: Using renamed "Muted.TLabel" style ---
        self.updated_lbl = ttk.Label(card, text="Last updated: --", style="Muted.TLabel")
        self.updated_lbl.pack(side=BOTTOM, fill=X)
        # Suggestions / Avoidance card
        self.suggestions_frame = ttk.Frame(card, style="Gradient.TFrame")
        self.suggestions_frame.pack(fill=X, pady=(8, 0))
        self.suggestions_lbl = ttk.Label(self.suggestions_frame, text="Suggestions: —", style="Detail.TLabel", wraplength=700, justify=LEFT)
        self.suggestions_lbl.pack(fill=X)
        
    def _setup_hourly_tab(self):
        """Set up the 'Hourly' tab with a 24-hour interactive chart."""
        header = ttk.Frame(self.hourly_tab_frame)
        header.pack(fill=X, pady=(0,8))

        title = ttk.Label(header, text="24-Hour Forecast", style="Header.TLabel")
        title.pack(side=LEFT)

        # Chart area
        body = ttk.Frame(self.hourly_tab_frame)
        body.pack(fill=BOTH, expand=YES)

        if MATPLOTLIB_AVAILABLE:
            fig, ax = plt.subplots(figsize=(8,3), dpi=100)
            self._hourly_fig = fig
            self._hourly_ax = ax
            self._hourly_canvas = FigureCanvasTkAgg(fig, master=body)
            self._hourly_canvas.get_tk_widget().pack(fill=BOTH, expand=YES)
            # Placeholders
            self._hourly_line = None
            self._hourly_fill = None
            self._hourly_vline = None
        else:
            ttk.Label(body, text='Install matplotlib to view the interactive 24-hour graph.', style='Muted.TLabel').pack(padx=8, pady=8)

    def _get_24h_from_forecast(self, forecast_list, tz_offset=0):
        """Interpolate the 3-hourly forecast into 24 hourly points starting from current hour
        at the target location's local time (tz_offset in seconds).
        Returns list of dicts: {'dt': datetime, 'label': 'HH:00', 'temp': float, 'main': str}
        """
        try:
            now_local = datetime.utcnow() + timedelta(seconds=tz_offset)
            now_local = now_local.replace(minute=0, second=0, microsecond=0)
            targets = [now_local + timedelta(hours=i) for i in range(24)]

            # Build points from forecast_list using UTC timestamp + tz_offset
            pts = []
            for item in forecast_list:
                dt_local = datetime.utcfromtimestamp(item['dt']) + timedelta(seconds=tz_offset)
                dt_local = dt_local.replace(minute=0, second=0, microsecond=0)
                temp = item['main']['temp']
                main = item['weather'][0]['main'] if item.get('weather') else None
                pts.append((dt_local, float(temp), main))

            # Sort pts
            pts.sort(key=lambda x: x[0])

            result = []
            if not pts:
                return result

            for t in targets:
                # If an exact match
                exact = next((p for p in pts if p[0] == t), None)
                if exact:
                    result.append({'dt': t, 'label': t.strftime('%H:%M'), 'temp': exact[1], 'main': exact[2]})
                    continue

                # Find surrounding points
                before = None
                after = None
                for p in pts:
                    if p[0] < t:
                        before = p
                    if p[0] > t and after is None:
                        after = p
                        break

                if before and after:
                    total = (after[0] - before[0]).total_seconds()
                    if total == 0:
                        temp = before[1]
                        frac = 0
                    else:
                        frac = (t - before[0]).total_seconds() / total
                        temp = before[1] + (after[1] - before[1]) * frac
                    main = before[2] if frac < 0.5 else after[2]
                elif before and not after:
                    temp = before[1]
                    main = before[2]
                elif after and not before:
                    temp = after[1]
                    main = after[2]
                else:
                    temp = pts[0][1]
                    main = pts[0][2]

                result.append({'dt': t, 'label': t.strftime('%H:%M'), 'temp': temp, 'main': main})

            return result
        except Exception:
            return []

    def _update_hourly_chart(self, hourly):
        """Update the embedded 24-hour chart using interpolated hourly data."""
        try:
            if not MATPLOTLIB_AVAILABLE or not hasattr(self, '_hourly_ax'):
                return

            if not hourly:
                return

            ax = self._hourly_ax
            fig = self._hourly_fig
            canvas = self._hourly_canvas
            ax.clear()

            times = [h['label'] for h in hourly]
            temps = [h['temp'] for h in hourly]

            x = list(range(len(times)))

            # --- Attractive Styling ---
            bg_color = self.style.lookup('TFrame', 'background')
            fg_color = self.style.lookup('TLabel', 'foreground')

            fig.patch.set_facecolor(bg_color)
            ax.set_facecolor(bg_color)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['bottom'].set_color(fg_color)
            ax.spines['left'].set_color(fg_color)
            ax.tick_params(axis='x', colors=fg_color)
            ax.tick_params(axis='y', colors=fg_color)
            ax.yaxis.label.set_color(fg_color)
            ax.title.set_color(fg_color)
            # --- End Styling ---

            # Plot line but animate the drawing by progressively revealing points
            line, = ax.plot(x, temps, marker='o', color=PALETTE['accent'], linewidth=3, markersize=5)
            area = ax.fill_between(x, temps, color=PALETTE['accent_soft'], alpha=0.35)

            ax.set_xticks(x[::2]) # Show every 2nd label
            ax.set_xticklabels([times[i] for i in x[::2]], rotation=45, ha='right')
            ax.set_ylabel('°C')
            ax.set_title("Next 24 Hours")
            ax.grid(alpha=0.2)

            fig.tight_layout()
            canvas.draw()
            
            # attach mplcursors if available
            try:
                if MPLCURSORS_AVAILABLE:
                    mplcursors.cursor(ax.lines, hover=True)
            except Exception:
                pass
                
        except Exception as e:
            print(f"Error updating today chart: {e}")
            
    def _setup_forecast_tab(self):
        """Set up the forecast tab with 5 visual day cards."""
        
        # The main tab frame now has padding
        self.forecast_tab_frame.configure(padding=20)

        # Main container
        container = ttk.Frame(self.forecast_tab_frame)
        container.pack(fill=BOTH, expand=YES)
        
        # --- NEW ---
        # The left frame is now the ScrolledFrame
        # --- MODIFIED: Set autohide=False to make scrollbar always visible ---
        left_scroll_frame = ScrolledFrame(container, autohide=False)
        left_scroll_frame.pack(side=LEFT, fill='y', expand=NO, padx=(0, 10)) # Changed fill and expand

        # Cards are packed into left_scroll_frame.container
        left = left_scroll_frame.container 
        # --- END NEW ---

        right = ttk.Frame(container)
        right.pack(side=RIGHT, fill=BOTH, expand=YES, padx=(10, 0)) # Fills remaining space

        # Create 5 forecast cards and store them for updates
        self.forecast_cards = []
        for i in range(5):
            card = ForecastCard(left) # 'left' now refers to the scrollable container
            card.pack(side=TOP, fill=X, expand=NO, padx=5, pady=4) 
            # Click a forecast card to view full-day hourly graph / details
            card.bind("<Button-1>", lambda e, idx=i: self._on_forecast_card_click(idx))
            # --- NEW: Hover effect for card ---
            card.bind("<Enter>", lambda e, c=card: c.configure(style="CardHover.TFrame"))
            card.bind("<Leave>", lambda e, c=card: c.configure(style="Card.TFrame"))
            self.forecast_cards.append(card)

        # Matplotlib area in the right pane (embedded chart)
        if MATPLOTLIB_AVAILABLE:
            fig, ax = plt.subplots(figsize=(6,3), dpi=100)
            self._forecast_fig = fig
            self._forecast_ax = ax
            self._forecast_canvas = FigureCanvasTkAgg(fig, master=right)
            self._forecast_canvas.get_tk_widget().pack(fill=BOTH, expand=YES)
        else:
            ttk.Label(right, text='Install matplotlib for interactive charts', style='Muted.TLabel').pack(padx=8, pady=8)
            
    def _setup_map_tab(self):
        """Set up the weather map tab."""
        try:
            self.map_widget = tkintermapview.TkinterMapView(self.map_tab,
                                                            width=800,
                                                            height=600,
                                                            corner_radius=0)
            self.map_widget.pack(fill=BOTH, expand=YES)
            
            self.map_widget.set_position(51.5074, -0.1278) # Default: London
            self.map_widget.set_zoom(10)
            
            self._update_map_theme()
            
        except Exception as e:
            ttk.Label(self.map_tab,
                      text=f"Could not load map: {str(e)}\nMake sure you are connected to the internet.",
                      wraplength=400,
                      justify=CENTER).pack(pady=20, padx=20)
            
    def _update_map_theme(self):
        """Set map tile server based on the current theme."""
        if not hasattr(self, 'map_widget'):
            return
            
        # Locked to light theme, so only standard OSM tile is needed
        self.map_widget.set_tile_server("https://a.tile.openstreetmap.org/{z}/{x}/{y}.png", max_zoom=19)
            
    def _update_clock(self):
        """Updates the live clock every second."""
        try:
            # Check if weather data is loaded and has a timezone offset
            if hasattr(self, '_tz_offset'):
                # Calculate local time at the location
                now_utc = datetime.utcnow()
                local_time = now_utc + timedelta(seconds=self._tz_offset)
                time_str = local_time.strftime("%I:%M:%S %p")
            else:
                # Default to system time if no weather data is loaded
                local_time = datetime.now()
                time_str = local_time.strftime("%I:%M:%S %p")
            
            if self.clock_lbl:
                self.clock_lbl.configure(text=time_str)
        except Exception as e:
            # Fallback in case of error
            if self.clock_lbl:
                self.clock_lbl.configure(text="--:--:--")
            print(f"Error updating clock: {e}")
        
        # Schedule next update
        self.after(1000, self._update_clock)

    def _style_mini_ax(self, ax, bg_color):
        """(REMOVED) Helper to style the minimal sparkline graph"""
        pass

    def _update_mini_graph(self, hourly_data):
        """(REMOVED) Updates the 24h mini-graph (sparkline) in the header."""
        pass

    def _update_labels_style(self):
        """Force-update styles for labels on the gradient frame."""
        # This is necessary because these labels don't auto-update
        # their foreground color from the theme.
        self.location_lbl.configure(style="Location.TLabel")
        self.icon_lbl.configure(style="Icon.TLabel")
        self.temp_lbl.configure(style="Temp.TLabel")
        self.condition_lbl.configure(style="Condition.TLabel")
        self.sunrise_lbl.configure(style="Detail.TLabel")
        self.sunset_lbl.configure(style="Detail.TLabel")
        # --- FIX: Using renamed "Muted.TLabel" style ---
        self.updated_lbl.configure(style="Muted.TLabel")

    # --- Loading overlay and small UI helpers (improves perceived performance) ---
    def _create_loading_overlay(self):
        """Create a semi-transparent top-level used as a loading overlay.
        Using a Toplevel allows setting partial transparency on supported platforms.
        """
        self.loading_win = tk.Toplevel(self)
        self.loading_win.withdraw()
        self.loading_win.overrideredirect(True)
        self.loading_win.attributes('-topmost', True)
        try:
            # Semi-transparent overlay if supported
            self.loading_win.attributes('-alpha', 0.45)
        except Exception:
            pass

        frame = ttk.Frame(self.loading_win, padding=20)
        frame.pack(expand=YES, fill=BOTH)
        self._loading_pb = ttk.Progressbar(frame, mode='indeterminate', bootstyle='info')
        self._loading_pb.pack(padx=20, pady=20)

    def _show_loading(self):
        """Show the loading overlay and start spinner."""
        try:
            x = self.winfo_rootx(); y = self.winfo_rooty(); w = self.winfo_width(); h = self.winfo_height()
            self.loading_win.geometry(f"{w}x{h}+{x}+{y}")
            self.loading_win.deiconify()
            self._loading_pb.start(10)
        except Exception:
            # Fallback: update status label
            try: self.status_lbl.configure(text='Loading...')
            except Exception: pass

    def _hide_loading(self):
        """Hide the loading overlay and stop spinner."""
        try:
            self._loading_pb.stop()
            self.loading_win.withdraw()
        except Exception:
            try: self.status_lbl.configure(text='Ready')
            except Exception: pass

    def _animate_value(self, label, target, fmt='{:.0f}°C', duration=600):
        """Animate numeric transition for a label from previous value to target.
        This makes temperature changes feel smooth (micro-interaction).
        """
        try:
            start = self._last_temp_value if self._last_temp_value is not None else 0
            end = float(target)
            steps = max(6, int(duration / 50))
            steps = int(steps)
            delta = (end - start) / steps
            i = 0

            def step():
                nonlocal i, start
                i += 1
                val = start + delta * i
                label.configure(text=fmt.format(val))
                if i < steps:
                    self.after(50, step)
                else:
                    # finalize
                    self._last_temp_value = end
                    label.configure(text=fmt.format(end))

            step()
        except Exception:
            # fallback to direct set
            label.configure(text=fmt.format(target))

    def search_weather(self):
        """Fetch weather data for the searched location."""
        if self.loading:
            return
            
        location = self.location_var.get().strip()
        if not location:
            return
        
        # Removed Demo mode check

        if API_KEY == "YOUR_API_KEY_HERE":
            messagebox.showerror("API Key Missing", 
                                 "Please add your OpenWeatherMap API key to the Python script.")
            return

        self.loading = True
        self.search_btn.configure(state="disabled", text="Loading...")
        self.location_lbl.configure(text="Loading...")
        
        thread = threading.Thread(target=self._fetch_weather, args=(location,))
        thread.daemon = True
        thread.start()
        
    def _fetch_weather(self, location):
        """Fetch weather data in background thread."""
        try:
            now_ts = time.time()
            key = location.lower()
            # Return cached response if fresh
            cached = self._cache.get(key)
            if cached and (now_ts - cached[0] < CACHE_TTL):
                data_package = cached[1]
                self.after(0, lambda: self._update_weather_ui(data_package))
                return
            # --- Fetch Current Weather ---
            current_url = CURRENT_URL.format(city=location, key=API_KEY)
            current_response = requests.get(current_url, timeout=10)
            current_response.raise_for_status() # Raise exception for 4xx/5xx errors
            current_data = current_response.json()
            
            # --- Fetch Forecast ---
            forecast_url = FORECAST_URL.format(city=location, key=API_KEY)
            forecast_response = requests.get(forecast_url, timeout=10)
            forecast_response.raise_for_status()
            forecast_data = forecast_response.json()
            
            # --- Combine Data ---
            data_package = {
                "current": current_data,
                "forecast_raw": forecast_data,
                "last_updated": datetime.now().strftime("%I:%M %p")
            }

            # store in cache
            try:
                self._cache[key] = (time.time(), data_package)
            except Exception:
                pass
            
            self._save_preference(CONFIG_CITY_FILE, location)
            self.after(0, lambda: self._update_weather_ui(data_package))
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                self.after(0, lambda: self._show_error(f"City not found: {location}"))
            elif e.response.status_code == 401:
                self.after(0, lambda: self._show_error("Invalid API Key. Please check your key in the script."))
            else:
                self.after(0, lambda: self._show_error(f"HTTP Error: {e}"))
        except requests.exceptions.ConnectionError:
            self.after(0, lambda: self._show_error("Network Error: Could not connect to weather service."))
        except Exception as e:
            self.after(0, lambda: self._show_error(f"An unexpected error occurred: {e}"))
        finally:
            self.after(0, self._end_loading)

    def _process_forecast_data(self, forecast_list, tz_offset=0):
        """
        Process the raw 3-hour forecast list into a 5-day summary.
        """
        daily_data = {}
        # Use local date at target timezone
        today = (datetime.utcnow() + timedelta(seconds=tz_offset)).date()

        for item in forecast_list:
            item_date = (datetime.utcfromtimestamp(item['dt']) + timedelta(seconds=tz_offset)).date()

            # Skip today's data
            if item_date == today:
                continue

            if item_date not in daily_data:
                daily_data[item_date] = {
                    'temps': [],
                    'conditions': [],
                    'icons': []
                }
            
            daily_data[item_date]['temps'].append(item['main']['temp'])
            daily_data[item_date]['conditions'].append(item['weather'][0]['description'])
            daily_data[item_date]['icons'].append(item['weather'][0]['main'])

        processed_forecast = []
        # Sort by date and take the first 5 days
        for day in sorted(daily_data.keys())[:5]:
            temps = daily_data[day]['temps']
            icons = daily_data[day]['icons']
            
            # Find the most common icon for the day
            try:
                most_common_icon = Counter(icons).most_common(1)[0][0]
            except IndexError:
                most_common_icon = "Default"

            processed_forecast.append({
                'day_name': day.strftime('%A'), # e.g., "Tuesday"
                'temp_max': max(temps),
                'temp_min': min(temps),
                'icon_main': most_common_icon,
                'icon_char': WEATHER_ICONS.get(most_common_icon, WEATHER_ICONS["Default"]),
                'date_iso': day.isoformat()
            })
            
        return processed_forecast

    def _group_hourly_by_day(self, forecast_list, tz_offset=0):
        """Group the 3-hour forecast items by ISO date string -> list(items).
        Returns a dict like {'2025-10-30': [item, ...], ...}
        """
        grouped = {}
        for item in forecast_list:
            item_date = (datetime.utcfromtimestamp(item['dt']) + timedelta(seconds=tz_offset)).date()
            iso = item_date.isoformat()
            if iso not in grouped:
                grouped[iso] = []
            grouped[iso].append(item)
        return grouped

    def _on_forecast_card_click(self, idx):
        """Open daily/hourly view for the forecast card at index idx."""
        try:
            # Map index to processed forecast entry
            forecast_raw = self.weather_data.get('forecast_raw', {})
            if not forecast_raw:
                return
            tz_offset = forecast_raw.get('city', {}).get('timezone', 0)
            processed = self._process_forecast_data(forecast_raw.get('list', []), tz_offset=tz_offset)
            if idx >= len(processed):
                return
            day_entry = processed[idx]
            iso = day_entry.get('date_iso')
            grouped = self._group_hourly_by_day(forecast_raw.get('list', []), tz_offset=tz_offset)
            hourly = grouped.get(iso, [])
            if not hourly:
                messagebox.showinfo("No data", "No hourly data available for this day.")
                return
            # Show the daily/hourly graph
            self._show_daily_graph(day_entry['day_name'], hourly, tz_offset=tz_offset)
        except Exception as e:
            print(f"Error opening daily graph: {e}")

    def _show_daily_graph(self, day_name, hourly_list, tz_offset=0):
        """Show a Toplevel window with an hourly temperature line chart for the selected day.
        Uses matplotlib if available; otherwise shows a textual breakdown.
        """
        if MATPLOTLIB_AVAILABLE:
            try:
                times = [(datetime.utcfromtimestamp(it['dt']) + timedelta(seconds=tz_offset)).strftime('%H:%M') for it in hourly_list]
                temps = [it['main']['temp'] for it in hourly_list]

                win = tk.Toplevel(self)
                win.title(f"Hourly - {day_name}")
                win.geometry('700x420')

                fig, ax = plt.subplots(figsize=(7,3.5), dpi=100)
                
                # --- Attractive Styling for popup ---
                bg_color = self.style.lookup('TFrame', 'background')
                fg_color = self.style.lookup('TLabel', 'foreground')

                fig.patch.set_facecolor(bg_color)
                ax.set_facecolor(bg_color)
                ax.spines['top'].set_visible(False)
                ax.spines['right'].set_visible(False)
                ax.spines['bottom'].set_color(fg_color)
                ax.spines['left'].set_color(fg_color)
                ax.tick_params(axis='x', colors=fg_color)
                ax.tick_params(axis='y', colors=fg_color)
                ax.yaxis.label.set_color(fg_color)
                ax.xaxis.label.set_color(fg_color)
                ax.title.set_color(fg_color)
                # --- End Styling ---
                
                ax.plot(times, temps, marker='o', linestyle='-', color='#ffc107', linewidth=3, markersize=6) # NEW Amber/Yellow
                ax.set_title(f"Hourly Temperatures — {day_name}")
                ax.set_ylabel('Temperature (°C)')
                ax.set_xlabel('Time')
                ax.grid(alpha=0.25)
                fig.tight_layout()

                canvas = FigureCanvasTkAgg(fig, master=win)
                canvas.draw()
                canvas.get_tk_widget().pack(fill=BOTH, expand=YES)

                # Add interactive tooltips with mplcursors if available
                try:
                    if MPLCURSORS_AVAILABLE:
                        cursor = mplcursors.cursor(ax.lines, hover=True)
                        @cursor.connect("add")
                        def _(sel):
                            x, y = sel.target
                            try:
                                idx = int(round(x))
                                label = times[idx]
                            except Exception:
                                label = f"{x:.0f}"
                            sel.annotation.set(text=f"{label}\n{y:.1f} °C")
                except Exception:
                    pass
            except Exception as e:
                messagebox.showerror("Graph Error", f"Could not render graph: {e}")
        else:
            # Fallback: show textual hourly list
            win = tk.Toplevel(self)
            win.title(f"Hourly - {day_name}")
            txt = tk.Text(win, wrap='word', height=20)
            for it in hourly_list:
                t = (datetime.utcfromtimestamp(it['dt']) + timedelta(seconds=tz_offset)).strftime('%H:%M')
                temp = it['main']['temp']
                desc = it['weather'][0]['description']
                txt.insert('end', f"{t} — {temp:.1f}°C — {desc}\n")
            txt.config(state='disabled')
            txt.pack(fill=BOTH, expand=YES)

    def _generate_suggestions(self, current, forecast_raw):
        """Generate a short list of avoidance/safety suggestions based on current conditions
        and the upcoming forecast. Returns a single concatenated string.
        """
        suggestions = []

        try:
            main = current['weather'][0]['main']
            desc = current['weather'][0]['description']
            wind = current['wind']['speed']
            temp = current['main']['temp']
            uvi = None
            # try to read uvi if present in current or forecast (OneCall provides uvi)
            if 'uvi' in current:
                uvi = current['uvi']
        except Exception:
            main = None; desc = None; wind = 0; temp = None; uvi = None

        # Basic rules
        if main and main in ('Rain', 'Thunderstorm', 'Drizzle'):
            suggestions.append('Rain expected — avoid outdoor events; carry an umbrella or seek indoor alternatives.')
        if wind and wind >= 10:
            suggestions.append('High winds — avoid boating and secure loose outdoor objects.')
        if temp is not None and temp >= 33:
            suggestions.append('Heat alert — avoid intense outdoor exercise during peak hours; stay hydrated and seek shade.')
        if temp is not None and temp <= 0:
            suggestions.append('Freezing temperatures — dress warmly and avoid prolonged exposure.')
        if uvi is not None and uvi >= 7:
            suggestions.append('High UV index — wear sunscreen and protective clothing.')

        # Look for days with heavy rain probability in forecast (simple heuristic)
        try:
            heavy_rain_days = set()
            for item in forecast_raw.get('list', []):
                pop = item.get('pop', 0)
                if pop >= 0.6:
                    d = datetime.fromtimestamp(item['dt']).date().isoformat()
                    heavy_rain_days.add(d)
            if heavy_rain_days:
                suggestions.append('Some upcoming days have high rain probability — consider indoor plans for those days.')
        except Exception:
            pass

        if not suggestions:
            suggestions.append('No major hazards detected. Enjoy your day — check back for updates.')

        return ' \n'.join(suggestions)

    def _update_weather_ui(self, data):
        """
        Update UI with new weather data.
        This is the main orchestrator function.
        """
        self.weather_data = data
        
        try:
            # --- Parse Core Data ---
            current = data["current"]
            forecast_raw = data.get("forecast_raw", {})
            forecast_list = forecast_raw.get("list", [])
            tz_offset = forecast_raw.get('city', {}).get('timezone', 0)
            self._tz_offset = tz_offset # Store for other methods
            
            # --- Call Sub-Updaters ---
            self._update_current_tab_ui(current, forecast_raw, tz_offset, data["last_updated"])
            self._update_map_ui(current)
            self._update_hourly_tab_ui(forecast_list, tz_offset)
            self._update_forecast_tab_ui(forecast_list, tz_offset)

        except KeyError as e:
            self._show_error(f"Error parsing weather data: Missing key {e}")
            return
        except Exception as e:
            print(f"Error during UI update: {e}")


    def _update_current_tab_ui(self, current, forecast_raw, tz_offset, last_updated):
        """Updates all widgets on the 'Current' tab."""
        try:
            location_name = f"{current['name']}, {current['sys']['country']}"
            temp = current['main']['temp']
            feels_like = current['main']['feels_like']
            humidity = current['main']['humidity']
            pressure = current['main']['pressure']
            wind_speed = current['wind']['speed']
            description = current['weather'][0]['description'].title()
            main_condition = current['weather'][0]['main']
            icon = WEATHER_ICONS.get(main_condition, WEATHER_ICONS["Default"])

            # Get sunrise/sunset (timestamps)
            sunrise_ts = current['sys']['sunrise']
            sunset_ts = current['sys']['sunset']
            
            # Apply tz_offset to sunrise/sunset times
            sunrise_dt = datetime.utcfromtimestamp(sunrise_ts) + timedelta(seconds=tz_offset)
            sunset_dt = datetime.utcfromtimestamp(sunset_ts) + timedelta(seconds=tz_offset)
            
            sunrise_time = sunrise_dt.strftime("%I:%M %p")
            sunset_time = sunset_dt.strftime("%I:%M %p")

            # --- Update Widgets ---
            self._update_labels_style() # Ensure labels have correct gradient-fg
            self.location_lbl.configure(text=location_name)
            
            # Animate temperature change
            self._animate_value(self.temp_lbl, temp, fmt='{:.0f}°C')
            
            self.icon_lbl.configure(text=icon)
            self.condition_lbl.configure(text=description)
            self.updated_lbl.configure(text=f"Last updated: {last_updated}")
            
            # Update meters
            self.feels_like_meter.configure(amountused=int(feels_like))
            self.humidity_meter.configure(amountused=humidity)
            self.wind_meter.configure(amountused=int(wind_speed))
            self.pressure_meter.configure(amountused=pressure) 
            
            # Update sun times
            self.sunrise_lbl.configure(text=f"☀️ Sunrise: {sunrise_time}")
            self.sunset_lbl.configure(text=f"🌙 Sunset: {sunset_time}")
            
            # Update gradient background
            theme_colors = THEMES[self.theme_mode]["dynamic_bg"]
            colors = theme_colors.get(main_condition, theme_colors["Default"])
            self.gradient_card.update_gradient(colors[0], colors[1])

            # Update suggestions
            suggestions_text = self._generate_suggestions(current, forecast_raw)
            self.suggestions_lbl.configure(text=f"Suggestions: {suggestions_text}")

        except Exception as e:
            print(f"Error updating Current tab: {e}")

    def _update_map_ui(self, current):
        """Updates all widgets on the 'Map' tab."""
        try:
            if hasattr(self, 'map_widget'):
                coords = current['coord']
                lat, lon = coords['lat'], coords['lon']
                
                # Clear old marker
                if self.current_marker:
                    self.current_marker.delete()
                    
                self.map_widget.set_position(lat, lon)
                self.current_marker = self.map_widget.set_marker(lat, lon, text=current['name'])
                self.map_widget.set_zoom(10)
        except Exception as e:
            print(f"Error updating Map tab: {e}")

    def _update_hourly_tab_ui(self, forecast_list, tz_offset):
        """Updates all widgets on the 'Hourly' tab."""
        try:
            hourly_24h = self._get_24h_from_forecast(forecast_list, tz_offset=tz_offset)
            self._update_hourly_chart(hourly_24h)
        except Exception as e:
            print(f"Error updating Hourly tab: {e}")

    def _update_forecast_tab_ui(self, forecast_list, tz_offset):
        """Updates all widgets on the '5-Day Forecast' tab."""
        try:
            # --- Process and Update Forecast Cards ---
            processed_forecast = self._process_forecast_data(forecast_list, tz_offset=tz_offset)
            
            # Update forecast cards
            for i, card in enumerate(self.forecast_cards):
                if i < len(processed_forecast):
                    day_data = processed_forecast[i]
                    card.update_info(
                        day=day_data['day_name'],
                        icon_char=day_data['icon_char'],
                        temp_max=day_data['temp_max'],
                        temp_min=day_data['temp_min']
                    )
                    card.pack(side=TOP, fill=X, expand=NO, padx=5, pady=4)
                else:
                    card.pack_forget() # Hide extra cards
                    
            # --- Update embedded Forecast Chart (if present) ---
            if MATPLOTLIB_AVAILABLE and hasattr(self, '_forecast_ax'):
                ax = self._forecast_ax
                fig = self._forecast_fig
                ax.clear()

                # Plot daily highs and lows
                days = [d['day_name'] for d in processed_forecast]
                highs = [d['temp_max'] for d in processed_forecast]
                lows = [d['temp_min'] for d in processed_forecast]
                
                # --- Attractive Styling for 5-Day Chart ---
                bg_color = self.style.lookup('TFrame', 'background')
                fg_color = self.style.lookup('TLabel', 'foreground')

                fig.patch.set_facecolor(bg_color)
                ax.set_facecolor(bg_color)
                ax.spines['top'].set_visible(False)
                ax.spines['right'].set_visible(False)
                ax.spines['bottom'].set_color(fg_color)
                ax.spines['left'].set_color(fg_color)
                ax.tick_params(axis='x', colors=fg_color)
                ax.tick_params(axis='y', colors=fg_color)
                ax.yaxis.label.set_color(fg_color)
                ax.title.set_color(fg_color)
                # --- End Styling ---

                x = range(len(days))
                ax.plot(x, highs, marker='o', color=PALETTE['accent'], label='High', linewidth=3, markersize=6)
                ax.plot(x, lows, marker='o', color='#ffc107', label='Low', linewidth=3, markersize=6) # NEW Amber/Yellow
                ax.fill_between(x, lows, highs, color=PALETTE['accent_soft'], alpha=0.35)
                ax.set_xticks(x)
                ax.set_xticklabels(days, rotation=10)
                ax.set_title('5-Day Forecast')
                ax.set_ylabel('Temperature (°C)')
                ax.grid(alpha=0.2)
                legend = ax.legend(frameon=False)
                # Set legend text color
                plt.setp(legend.get_texts(), color=fg_color)
                
                fig.tight_layout()
                try:
                    self._forecast_canvas.draw()
                except Exception:
                    pass

                # Attach simple hover tooltips using mplcursors
                try:
                    if MPLCURSORS_AVAILABLE:
                        mplcursors.cursor(ax.lines, hover=True)
                except Exception:
                    pass
        except Exception as e:
            print(f"Error updating Forecast tab: {e}")
            
    def _show_error(self, message):
        """Show error message to user."""
        self.location_lbl.configure(text="Error")
        messagebox.showerror("Weather Error", message)
        
    def _end_loading(self):
        """Reset loading state."""
        self.loading = False
        self.search_btn.configure(state="normal", text="Search")
        
if __name__ == "__main__":
    # A quick check to ensure dependencies are installed
    try:
        import requests
        import tkintermapview
        import ttkbootstrap
    except ImportError as e:
        print(f"Error: Required library not found: {e.name}")
        print("Please install all required libraries:")
        print("   pip install requests tkintermapview ttkbootstrap")
        exit()

    app = ModernWeatherDashboard()
    app.mainloop()
