// Club names and kit colours (2026-27 Premier League), keyed by FPL short name.
// Unknown codes fall back to neutral colours, so a promoted club never breaks the page.
export const TEAMS = {
  ARS: { name: 'Arsenal', c1: '#EF0107', c2: '#FFFFFF' },
  AVL: { name: 'Aston Villa', c1: '#670E36', c2: '#95BFE5' },
  BHA: { name: 'Brighton', c1: '#0057B8', c2: '#FFFFFF' },
  BOU: { name: 'Bournemouth', c1: '#DA291C', c2: '#111111' },
  BRE: { name: 'Brentford', c1: '#E30613', c2: '#FFFFFF' },
  CHE: { name: 'Chelsea', c1: '#034694', c2: '#DBA111' },
  COV: { name: 'Coventry', c1: '#6CABDD', c2: '#FFFFFF' },
  CRY: { name: 'Crystal Palace', c1: '#1B458F', c2: '#C4122E' },
  EVE: { name: 'Everton', c1: '#003399', c2: '#FFFFFF' },
  FUL: { name: 'Fulham', c1: '#F5F5F5', c2: '#111111' },
  HUL: { name: 'Hull City', c1: '#F5A12D', c2: '#111111' },
  IPS: { name: 'Ipswich', c1: '#3A64A3', c2: '#FFFFFF' },
  LEE: { name: 'Leeds', c1: '#FFFFFF', c2: '#1D428A' },
  LIV: { name: 'Liverpool', c1: '#C8102E', c2: '#00B2A9' },
  MCI: { name: 'Man City', c1: '#6CABDD', c2: '#1C2C5B' },
  MUN: { name: 'Man Utd', c1: '#DA291C', c2: '#FBE122' },
  NEW: { name: 'Newcastle', c1: '#241F20', c2: '#FFFFFF' },
  NFO: { name: "Nott'm Forest", c1: '#DD0000', c2: '#FFFFFF' },
  SUN: { name: 'Sunderland', c1: '#EB172B', c2: '#FFFFFF' },
  TOT: { name: 'Spurs', c1: '#F5F5F5', c2: '#132257' },
  WHU: { name: 'West Ham', c1: '#7A263A', c2: '#1BB1E7' },
  WOL: { name: 'Wolves', c1: '#FDB913', c2: '#231F20' },
  BUR: { name: 'Burnley', c1: '#6C1D45', c2: '#99D6EA' },
  LEI: { name: 'Leicester', c1: '#003090', c2: '#FDBE11' },
  SOU: { name: 'Southampton', c1: '#D71920', c2: '#FFFFFF' },
  SHU: { name: 'Sheffield Utd', c1: '#EE2737', c2: '#FFFFFF' },
};

export function team(code) {
  return TEAMS[code] || { name: code, c1: '#5d6b63', c2: '#d6d9d2' };
}
