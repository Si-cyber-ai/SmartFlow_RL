"""SVG interpolation between actual simulator snapshots; no invented traffic."""
from html import escape
from .theme import tokens

def _positions(data):
    positions = {}
    for direction, ids in data['queues'].items():
        spacing = min(29., 205. / max(len(ids), 1))
        for i, vehicle_id in enumerate(ids):
            distance = 213 - i * spacing
            x, y = {'N': (278, distance), 'S': (322, 577-distance),
                    'E': (577-distance, 278), 'W': (distance, 322)}[direction]
            w, h = (15, min(23, spacing*.78)) if direction in ('N', 'S') else (min(23, spacing*.78), 15)
            positions[vehicle_id] = (direction, x, y, w, h)
    return positions


def intersection_svg(data, previous=None, animate=False, animation_seconds=.45, theme='dark'):
    """Queue cars equal current queues; separate departure ghosts show prior service.

    Positions are queue slots, not physical distances. Signal lamps always show
    the current snapshot; animated departures belong to the preceding second.
    """
    duration = max(.06, min(float(animation_seconds), 1.))
    t = tokens(theme)
    signal_colors = dict(green=t['success'], yellow=t['warning'], red=t['error'])
    old_positions = _positions(previous) if previous else {}
    positions = _positions(data)
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 600" role="img" aria-label="Live traffic intersection" style="width:100%;height:100%;display:block">',
           '<defs><pattern id="city-grid" width="24" height="24" patternUnits="userSpaceOnUse"><path d="M24 0H0V24" fill="none" stroke="#16283e" stroke-width=".5"/></pattern></defs>',
           '<rect width="600" height="600" rx="20" fill="#0B1626"/>',
           '<rect width="600" height="600" rx="20" fill="url(#city-grid)"/>',
           '<path d="M242 0H358V242H600V358H358V600H242V358H0V242H242Z" fill="#23354b" stroke="#48607a" stroke-width="2"/>',
           '<rect x="242" y="242" width="116" height="116" fill="#1a2b40"/>',
           '<path d="M300 0V237 M300 363V600 M0 300H237 M363 300H600" stroke="#d2b861" stroke-width="2" stroke-dasharray="12 9"/>',
           '<path d="M247 240H297 M303 360H353 M360 247V297 M240 303V353" stroke="#d7e8f5" stroke-width="4"/>']
    for pos in range(251, 353, 15):
        svg.append(f'<path d="M{pos} 246v7 M{pos} 347v7 M246 {pos}h7 M347 {pos}h7" stroke="#90a6bd" stroke-width="7"/>')
    for vehicle_id, (direction, x, y, w, h) in positions.items():
        old = old_positions.get(vehicle_id)
        start_x, start_y = (old[1], old[2]) if old else {'N': (278, -25), 'S': (322, 625), 'E': (625, 278), 'W': (-25, 322)}[direction]
        svg.append(f'<g class="queued-vehicle" data-vehicle-id="{vehicle_id}" data-direction="{direction}" transform="translate({x:.2f} {y:.2f})"><title>Vehicle {vehicle_id}</title>')
        if animate and (start_x != x or start_y != y):
            svg.append(f'<animateTransform attributeName="transform" type="translate" from="{start_x:.2f} {start_y:.2f}" to="{x:.2f} {y:.2f}" dur="{duration}s" fill="freeze"/>')
        color = '#38BDF8' if direction in ('N', 'S') else '#2DD4BF'
        svg.append(f'<rect width="{w:.2f}" height="{h:.2f}" rx="3" fill="{color}" stroke="#b9f4ff" stroke-width=".6"/>')
        if min(w, h) >= 6:
            svg.append(f'<rect x="2" y="2" width="{max(1,w-4):.2f}" height="{max(1,h*.24):.2f}" rx="1" fill="#15374b"/>')
        svg.append('</g>')
    if animate:
        for vehicle in data['departures']:
            direction, vehicle_id = vehicle['direction'], vehicle['id']
            old = old_positions.get(vehicle_id)
            start_x, start_y = (old[1], old[2]) if old else {'N': (278, 0), 'S': (322, 600), 'E': (600, 278), 'W': (0, 322)}[direction]
            end_x, end_y = {'N': (278, 625), 'S': (322, -25), 'E': (-25, 278), 'W': (625, 322)}[direction]
            w, h = (15, 23) if direction in ('N', 'S') else (23, 15)
            svg.append(f'<g class="departed-vehicle" data-vehicle-id="{vehicle_id}" opacity="0"><title>Departed {direction} #{vehicle_id} in previous second</title>'
                       f'<rect width="{w}" height="{h}" rx="3" fill="#a7f3d0"/>'
                       f'<animateTransform attributeName="transform" type="translate" from="{start_x:.2f} {start_y:.2f}" to="{end_x} {end_y}" dur="{duration}s" fill="freeze"/>'
                       f'<animate attributeName="opacity" values="1;1;0" keyTimes="0;.85;1" dur="{duration}s" fill="freeze"/></g>')
    for direction in ('N', 'S', 'E', 'W'):
        x, y = {'N': (213, 211), 'S': (370, 370), 'E': (370, 211), 'W': (213, 370)}[direction]
        svg.append(f'<g aria-label="{direction} signal {data["signals"][direction]}"><rect x="{x}" y="{y}" width="17" height="45" rx="7" fill="#060e19" stroke="#48607a"/>')
        for i, signal in enumerate(('red', 'yellow', 'green')):
            active = data['signals'][direction] == signal
            svg.append(f'<circle cx="{x+8.5}" cy="{y+8+i*14}" r="4.5" fill="{signal_colors[signal] if active else "#263548"}"/>')
        svg.append('</g>')
        x, y = {'N': (150, 65), 'S': (450, 535), 'E': (480, 155), 'W': (100, 450)}[direction]
        name = {'N': 'NORTH', 'S': 'SOUTH', 'E': 'EAST', 'W': 'WEST'}[direction]
        count = len(data['queues'][direction])
        svg.append(f'<text x="{x}" y="{y}" text-anchor="middle" fill="#91aac3" font-family="system-ui,sans-serif" font-size="12" letter-spacing="2">{name}</text>'
                   f'<text x="{x}" y="{y+34}" text-anchor="middle" fill="#e6f7ff" font-family="system-ui,sans-serif" font-size="30" font-weight="700">{count}</text>'
                   f'<text x="{x}" y="{y+52}" text-anchor="middle" fill="#6e8ba8" font-family="system-ui,sans-serif" font-size="10">QUEUED</text>')
    label = f'{data["time"]:03d}s · {data["status"].upper()}'
    svg.append(f'<text x="300" y="590" fill="#bfd8ee" text-anchor="middle" font-family="system-ui,sans-serif" font-size="11">{escape(label)}</text></svg>')
    # Apply centralized semantic tokens without touching geometry, IDs or timing.
    replacements = {'#0B1626': t['scene_background'], '#16283e': t['scene_grid'],
                    '#23354b': t['road_color'], '#48607a': t['border'], '#1a2b40': t['intersection'],
                    '#d2b861': t['road_centerline'], '#d7e8f5': t['road_markings'],
                    '#90a6bd': t['road_markings'], '#91aac3': t['scene_muted'], '#e6f7ff': t['scene_text'],
                    '#6e8ba8': t['scene_muted'], '#bfd8ee': t['scene_text'],
                    '#38BDF8': t['vehicle_ns'], '#2DD4BF': t['vehicle_ew'],
                    '#b9f4ff': t['vehicle_outline'], '#15374b': t['vehicle_window'],
                    '#a7f3d0': t['departed_vehicle'], '#060e19': t['signal_housing'], '#263548': t['signal_off']}
    rendered = ''.join(svg)
    for original, themed in replacements.items():
        rendered = rendered.replace(original, themed)
    return rendered


def intersection_document(data, previous=None, animate=False, animation_seconds=.45, theme='dark'):
    """Trusted iframe preserves native SVG animation without JavaScript/dependencies."""
    return ('<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1">'
            '<style>html,body{margin:0;background:' + tokens(theme)['scene_background'] + ';height:100%;overflow:hidden;}'
            'svg{max-width:100%;max-height:100%;margin:auto;}</style></head><body>' +
            intersection_svg(data, previous, animate, animation_seconds, theme) + '</body></html>')
