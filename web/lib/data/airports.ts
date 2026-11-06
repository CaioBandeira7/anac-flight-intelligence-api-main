/**
 * Reference list of major Brazilian airports (public geographic facts:
 * codes and approximate coordinates). Movement counts are NOT included here —
 * those come from a data provider.
 */
export interface AirportRef {
  icao: string;
  iata: string;
  name: string;
  city: string;
  uf: string;
  lat: number;
  lon: number;
}

export const AIRPORTS: AirportRef[] = [
  { icao: "SBGR", iata: "GRU", name: "Guarulhos", city: "São Paulo", uf: "SP", lat: -23.435, lon: -46.473 },
  { icao: "SBSP", iata: "CGH", name: "Congonhas", city: "São Paulo", uf: "SP", lat: -23.626, lon: -46.656 },
  { icao: "SBBR", iata: "BSB", name: "Brasília", city: "Brasília", uf: "DF", lat: -15.871, lon: -47.918 },
  { icao: "SBGL", iata: "GIG", name: "Galeão", city: "Rio de Janeiro", uf: "RJ", lat: -22.81, lon: -43.251 },
  { icao: "SBRJ", iata: "SDU", name: "Santos Dumont", city: "Rio de Janeiro", uf: "RJ", lat: -22.91, lon: -43.163 },
  { icao: "SBKP", iata: "VCP", name: "Viracopos", city: "Campinas", uf: "SP", lat: -23.007, lon: -47.134 },
  { icao: "SBCF", iata: "CNF", name: "Confins", city: "Belo Horizonte", uf: "MG", lat: -19.624, lon: -43.972 },
  { icao: "SBRF", iata: "REC", name: "Guararapes", city: "Recife", uf: "PE", lat: -8.126, lon: -34.923 },
  { icao: "SBSV", iata: "SSA", name: "Salvador", city: "Salvador", uf: "BA", lat: -12.909, lon: -38.331 },
  { icao: "SBFZ", iata: "FOR", name: "Pinto Martins", city: "Fortaleza", uf: "CE", lat: -3.776, lon: -38.532 },
  { icao: "SBPA", iata: "POA", name: "Salgado Filho", city: "Porto Alegre", uf: "RS", lat: -29.994, lon: -51.171 },
  { icao: "SBCT", iata: "CWB", name: "Afonso Pena", city: "Curitiba", uf: "PR", lat: -25.528, lon: -49.176 },
  { icao: "SBFL", iata: "FLN", name: "Hercílio Luz", city: "Florianópolis", uf: "SC", lat: -27.67, lon: -48.552 },
  { icao: "SBBE", iata: "BEL", name: "Val-de-Cans", city: "Belém", uf: "PA", lat: -1.379, lon: -48.476 },
  { icao: "SBEG", iata: "MAO", name: "Eduardo Gomes", city: "Manaus", uf: "AM", lat: -3.038, lon: -60.05 },
  { icao: "SBCY", iata: "CGB", name: "Marechal Rondon", city: "Cuiabá", uf: "MT", lat: -15.653, lon: -56.117 },
  { icao: "SBGO", iata: "GYN", name: "Santa Genoveva", city: "Goiânia", uf: "GO", lat: -16.632, lon: -49.221 },
  { icao: "SBSG", iata: "NAT", name: "São Gonçalo do Amarante", city: "Natal", uf: "RN", lat: -5.769, lon: -35.367 },
  { icao: "SBVT", iata: "VIX", name: "Eurico de Aguiar Salles", city: "Vitória", uf: "ES", lat: -20.258, lon: -40.286 },
  { icao: "SBSL", iata: "SLZ", name: "Marechal Cunha Machado", city: "São Luís", uf: "MA", lat: -2.585, lon: -44.234 },
];

export const airportByIata = (iata: string) => AIRPORTS.find((a) => a.iata === iata);

/** Illustrative route network used by the landing visuals (not traffic data). */
export const ILLUSTRATIVE_ROUTES: [string, string][] = [
  ["GRU", "BSB"], ["GRU", "REC"], ["GRU", "SSA"], ["GRU", "FOR"], ["GRU", "POA"],
  ["GRU", "MAO"], ["GRU", "BEL"], ["CGH", "SDU"], ["CGH", "CNF"], ["CGH", "CWB"],
  ["BSB", "MAO"], ["BSB", "BEL"], ["BSB", "FOR"], ["BSB", "CGB"], ["BSB", "SSA"],
  ["BSB", "GYN"], ["GIG", "REC"], ["GIG", "SSA"], ["VCP", "CNF"], ["VCP", "FLN"],
  ["CNF", "VIX"], ["REC", "NAT"], ["FOR", "SLZ"], ["POA", "FLN"], ["CWB", "POA"],
];

/** Simple equirectangular projection fitted to Brazil's bounding box. */
export function project(lat: number, lon: number, width: number, height: number) {
  const minLon = -74, maxLon = -34, minLat = -34, maxLat = 5.5;
  const x = ((lon - minLon) / (maxLon - minLon)) * width;
  const y = ((maxLat - lat) / (maxLat - minLat)) * height;
  return { x, y };
}
