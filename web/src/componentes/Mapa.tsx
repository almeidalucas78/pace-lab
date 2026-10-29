import 'leaflet/dist/leaflet.css'
import { MapContainer, Polyline, TileLayer } from 'react-leaflet'
import type { Amostra } from '../api/tipos'

// Tiles do OpenStreetMap (política: atribuição visível, HTTPS, sem download para uso offline).
// Para trocar de provedor, defina VITE_MAPA_TILES no web/.env.local.
const TILES = import.meta.env.VITE_MAPA_TILES || 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
const ATRIBUICAO = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'

export function Mapa({ amostras }: { amostras: Amostra[] }) {
  const pontos = amostras
    .filter((a) => a.lat != null && a.lon != null)
    .map((a) => [a.lat, a.lon] as [number, number])
  if (pontos.length < 2) return <div className="vazio">Treino sem GPS.</div>
  return (
    <MapContainer className="mapa" bounds={pontos} boundsOptions={{ padding: [20, 20] }} scrollWheelZoom={false}>
      <TileLayer url={TILES} attribution={ATRIBUICAO} />
      <Polyline positions={pontos} pathOptions={{ color: '#2563eb', weight: 4 }} />
    </MapContainer>
  )
}
