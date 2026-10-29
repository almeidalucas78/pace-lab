"""Leitura dos arquivos de treino (GPX, TCX, FIT, com ou sem .gz) para um formato comum."""
from __future__ import annotations

import gzip
import io
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Point:
    time: datetime
    lat: float | None = None
    lon: float | None = None
    ele: float | None = None
    hr: float | None = None
    cadence: float | None = None   # como vem no arquivo (TCX/FIT de corrida: por perna)
    speed: float | None = None     # m/s
    dist: float | None = None      # acumulada, se o arquivo trouxer


@dataclass
class ParsedFile:
    fmt: str
    sport_hint: str | None = None
    points: list[Point] = field(default_factory=list)


class UnsupportedFormat(Exception):
    pass


def _parse_time(s: str) -> datetime:
    dt = datetime.fromisoformat(s.strip().replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _strip_ns(root: ET.Element) -> ET.Element:
    for el in root.iter():
        if isinstance(el.tag, str) and "}" in el.tag:
            el.tag = el.tag.split("}", 1)[1]
    return root


def _f(text: str | None) -> float | None:
    if text is None or not text.strip():
        return None
    return float(text)


def parse_gpx(raw: bytes) -> ParsedFile:
    root = _strip_ns(ET.fromstring(raw.lstrip()))
    trk = root.find("trk")
    sport = (trk.findtext("type") or "").strip() if trk is not None else ""
    pts: list[Point] = []
    for p in root.iter("trkpt"):
        t = p.findtext("time")
        if not t:
            continue
        hr = cad = None
        for ext in p.iter():
            if ext.tag == "hr":
                hr = _f(ext.text)
            elif ext.tag in ("cad", "cadence"):
                cad = _f(ext.text)
        pts.append(Point(time=_parse_time(t), lat=_f(p.get("lat")), lon=_f(p.get("lon")),
                         ele=_f(p.findtext("ele")), hr=hr, cadence=cad))
    return ParsedFile(fmt="gpx", sport_hint=sport or None, points=pts)


def parse_tcx(raw: bytes) -> ParsedFile:
    root = _strip_ns(ET.fromstring(raw.lstrip()))
    act = root.find(".//Activity")
    if act is None:
        return ParsedFile(fmt="tcx")
    # Samsung grava a mesma hora em várias linhas (uma com FC, outra com velocidade): juntamos por horário.
    merged: dict[datetime, Point] = {}
    for tp in act.iter("Trackpoint"):
        t = tp.findtext("Time")
        if not t:
            continue
        ts = _parse_time(t)
        pt = merged.setdefault(ts, Point(time=ts))
        pos = tp.find("Position")
        if pos is not None:
            pt.lat = _f(pos.findtext("LatitudeDegrees"))
            pt.lon = _f(pos.findtext("LongitudeDegrees"))
        for attr, path in (("ele", "AltitudeMeters"), ("hr", "HeartRateBpm/Value"),
                           ("cadence", "Cadence"), ("dist", "DistanceMeters")):
            v = _f(tp.findtext(path))
            if v is not None:
                setattr(pt, attr, v)
        spd = tp.find(".//Speed")
        if spd is not None:
            pt.speed = _f(spd.text)
    return ParsedFile(fmt="tcx", sport_hint=act.get("Sport"), points=sorted(merged.values(), key=lambda p: p.time))


SEMICIRCLE = 180.0 / 2**31


def parse_fit(raw: bytes) -> ParsedFile:
    import fitdecode

    pts: list[Point] = []
    sport = None
    with fitdecode.FitReader(io.BytesIO(raw)) as fit:
        for frame in fit:
            if not isinstance(frame, fitdecode.FitDataMessage):
                continue
            if frame.name == "sport" and frame.has_field("sport"):
                sport = str(frame.get_value("sport"))
            elif frame.name == "session" and sport is None and frame.has_field("sport"):
                sport = str(frame.get_value("sport"))
            elif frame.name == "record" and frame.has_field("timestamp"):
                def val(*names):
                    for n in names:
                        if frame.has_field(n):
                            v = frame.get_value(n)
                            if v is not None:
                                return v
                    return None
                ts = val("timestamp")
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                lat, lon = val("position_lat"), val("position_long")
                pts.append(Point(
                    time=ts,
                    lat=lat * SEMICIRCLE if isinstance(lat, int) else None,
                    lon=lon * SEMICIRCLE if isinstance(lon, int) else None,
                    ele=val("enhanced_altitude", "altitude"),
                    hr=val("heart_rate"),
                    cadence=val("cadence"),
                    speed=val("enhanced_speed", "speed"),
                    dist=val("distance"),
                ))
    return ParsedFile(fmt="fit", sport_hint=sport, points=pts)


def parse_activity_file(name: str, raw: bytes) -> ParsedFile:
    lower = name.lower()
    if lower.endswith(".gz"):
        raw = gzip.decompress(raw)
        lower = lower[:-3]
    if lower.endswith(".gpx"):
        return parse_gpx(raw)
    if lower.endswith(".tcx"):
        return parse_tcx(raw)
    if lower.endswith(".fit"):
        return parse_fit(raw)
    raise UnsupportedFormat(name)
