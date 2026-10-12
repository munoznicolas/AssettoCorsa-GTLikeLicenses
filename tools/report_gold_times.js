const path = require('path');
const tests = require(path.join(__dirname, '../docs/Gran_Turismo_License_Tests.json'));

const formatTime = (totalSeconds) => {
  if (totalSeconds === null || totalSeconds === undefined || !isFinite(totalSeconds)) return 'N/A';
  const mins = Math.floor(totalSeconds / 60);
  const secs = (totalSeconds % 60).toFixed(3);
  return `${mins}:${secs.padStart(6, '0')}`;
};

function getGoldStatsPerGame(tests) {
  const grouped = tests.reduce((acc, t) => {
    if (!acc[t.game]) {
      acc[t.game] = {
        game: t.game,
        total: 0,
        timed: 0,
        special: 0,
        totalSec: 0,
        times: []
      };
    }
    const g = acc[t.game];
    g.total++;
    if (t.gold_seconds !== null && t.gold_seconds !== undefined) {
      g.timed++;
      g.totalSec += t.gold_seconds;
      g.times.push({
        sec: t.gold_seconds,
        code: t.code,
        car: t.car,
        track: t.track
      });
    } else {
      g.special++;
    }
    return acc;
  }, {});

  return Object.values(grouped).map(g => {
    g.times.sort((a, b) => a.sec - b.sec);
    const avg = g.timed > 0 ? g.totalSec / g.timed : 0;
    const median = g.times.length > 0
      ? g.times[Math.floor(g.times.length / 2)].sec
      : 0;

    const fastest = g.times[0];
    const slowest = g.times[g.times.length - 1];

    return {
      Game: g.game,
      Tests: g.total,
      Timed: g.timed,
      Special: g.special,
      'Total Gold Time': formatTime(g.totalSec),
      'Avg Gold': formatTime(avg),
      'Median Gold': formatTime(median),
      'Fastest Test': fastest ? `${formatTime(fastest.sec)} (${fastest.code})` : 'N/A',
      'Slowest Test': slowest ? `${formatTime(slowest.sec)} (${slowest.code})` : 'N/A'
    };
  });
}

const stats = getGoldStatsPerGame(tests);
console.log('\n=================== GRAN TURISMO LICENSE TESTS: GOLD MEDAL STATS ===================\n');
console.table(stats);
console.log('=====================================================================================\n');

