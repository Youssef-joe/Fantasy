// GET /api/fpl-team?id=<FPL entry id>
//
// Returns a manager's public FPL squad as of the last deadline: team name, bank and
// the 15 picks. The browser can't call the FPL API directly (FPL doesn't allow
// cross-origin requests), so this function fetches it server-side. It only accepts a
// numeric id and only ever calls fantasy.premierleague.com.

const FPL = 'https://fantasy.premierleague.com/api';
const HEADERS = { 'User-Agent': 'Mozilla/5.0 (compatible; fantasy-predictions)' };

async function fpl(path) {
  const res = await fetch(`${FPL}${path}`, { headers: HEADERS, signal: AbortSignal.timeout(8000) });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`FPL responded ${res.status}`);
  return res.json();
}

module.exports = async (req, res) => {
  const raw = String(req.query.id ?? '').trim();
  if (!/^\d{1,9}$/.test(raw) || Number(raw) < 1) {
    return res.status(400).json({ error: 'Enter your FPL team ID: the number in your team URL.' });
  }
  const id = Number(raw);

  try {
    const entry = await fpl(`/entry/${id}/`);
    if (!entry) return res.status(404).json({ error: `No FPL team found with ID ${id}.` });
    const gw = entry.current_event;
    if (!gw) {
      return res.status(409).json({ error: 'This team has not played a gameweek yet, so FPL has no public squad for it.' });
    }
    const picks = await fpl(`/entry/${id}/event/${gw}/picks/`);
    if (!picks) return res.status(404).json({ error: `No squad found for GW${gw}.` });

    res.setHeader('Cache-Control', 'public, s-maxage=300, stale-while-revalidate=600');
    return res.status(200).json({
      id,
      name: entry.name,
      manager: [entry.player_first_name, entry.player_last_name].filter(Boolean).join(' '),
      overall_rank: entry.summary_overall_rank ?? null,
      gameweek: gw,
      bank: (picks.entry_history?.bank ?? entry.last_deadline_bank ?? 0) / 10,
      value: (picks.entry_history?.value ?? entry.last_deadline_value ?? 0) / 10,
      active_chip: picks.active_chip ?? null,
      picks: picks.picks.map((p) => ({
        player_id: p.element,
        slot: p.position,
        is_captain: p.is_captain,
        is_vice_captain: p.is_vice_captain,
      })),
    });
  } catch (err) {
    console.error('fpl-team failed', id, err);
    return res.status(502).json({ error: 'FPL is not responding right now. Try again in a minute.' });
  }
};
