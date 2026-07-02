import { createClient } from 'genlayer-js';
import { studionet } from 'genlayer-js/chains';

const CONTRACT_ADDRESS = '0xfBd7304D927b8F201348368569a0C5b2fEAac8F0';

let readClient, writeClient, userAddress;

document.querySelector('#app').innerHTML = `
<div style="background:#0a0a0f;min-height:100vh;color:#e2e8f0;font-family:system-ui,sans-serif;">
  <div style="background:#111827;border-bottom:1px solid #1f2937;padding:16px 24px;display:flex;align-items:center;justify-content:space-between;">
    <div style="display:flex;align-items:center;gap:12px;">
      <div style="background:#f59e0b;width:32px;height:32px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:16px;">🧩</div>
      <span style="font-size:18px;font-weight:600;">Riddle Arena</span>
      <span style="background:#1e1b2e;color:#a78bfa;font-size:12px;padding:2px 10px;border-radius:20px;">GenLayer Studio</span>
    </div>
    <button id="connectBtn" onclick="window.connectWallet()" style="background:#f59e0b;color:#1a1a1a;padding:8px 20px;border-radius:8px;font-weight:600;cursor:pointer;border:none;font-size:14px;">Connect Wallet</button>
  </div>

  <div style="max-width:760px;margin:0 auto;padding:24px;">
    <div style="background:#111827;border:1px solid #1f2937;border-radius:12px;padding:24px;margin-bottom:20px;">
      <h2 style="font-size:20px;font-weight:600;margin:0 0 4px;">Create a Riddle</h2>
      <p style="color:#94a3b8;font-size:14px;margin:0 0 20px;">An AI validator generates a riddle. Every validator independently checks the riddle is fair before it goes live.</p>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
        <div>
          <label style="font-size:13px;color:#94a3b8;display:block;margin-bottom:6px;">Topic</label>
          <input id="c-topic" placeholder="e.g. astronomy" style="background:#1f2937;border:1px solid #374151;border-radius:8px;padding:10px 14px;color:#e2e8f0;width:100%;box-sizing:border-box;font-size:14px;outline:none;" />
        </div>
        <div>
          <label style="font-size:13px;color:#94a3b8;display:block;margin-bottom:6px;">Difficulty</label>
          <select id="c-difficulty" style="background:#1f2937;border:1px solid #374151;border-radius:8px;padding:10px 14px;color:#e2e8f0;width:100%;box-sizing:border-box;font-size:14px;outline:none;">
            <option value="easy">Easy</option>
            <option value="medium" selected>Medium</option>
            <option value="hard">Hard</option>
          </select>
        </div>
      </div>
      <button onclick="window.createRiddle()" style="background:#f59e0b;color:#1a1a1a;padding:10px 20px;border-radius:8px;font-weight:600;cursor:pointer;border:none;margin-top:16px;">Generate Riddle</button>
      <div id="create-result"></div>
    </div>

    <div style="background:#111827;border:1px solid #1f2937;border-radius:12px;padding:24px;margin-bottom:20px;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
        <h2 style="font-size:20px;font-weight:600;margin:0;">Riddles</h2>
        <button onclick="window.loadRiddles()" style="background:#1f2937;color:#94a3b8;padding:6px 14px;border-radius:6px;font-size:13px;cursor:pointer;border:none;">↺ Refresh</button>
      </div>
      <p style="color:#94a3b8;font-size:14px;margin:0 0 16px;">Pick an unsolved riddle and submit your guess. First correct answer wins the points.</p>
      <div id="riddle-list"><p style="color:#4b5563;font-size:14px;margin:0;">Loading...</p></div>
    </div>

    <div style="background:#111827;border:1px solid #1f2937;border-radius:12px;padding:24px;">
      <h2 style="font-size:20px;font-weight:600;margin:0 0 4px;">Player Stats</h2>
      <p style="color:#94a3b8;font-size:14px;margin:0 0 16px;">Look up any player's score.</p>
      <div style="display:flex;gap:10px;">
        <input id="p-name" placeholder="player name" style="background:#1f2937;border:1px solid #374151;border-radius:8px;padding:10px 14px;color:#e2e8f0;flex:1;box-sizing:border-box;font-size:14px;outline:none;" />
        <button onclick="window.loadPlayer()" style="background:#1f2937;color:#94a3b8;padding:10px 20px;border-radius:8px;cursor:pointer;border:none;white-space:nowrap;">Look Up</button>
      </div>
      <div id="player-result"></div>
    </div>
  </div>
</div>
`;

const style = document.createElement('style');
style.textContent = '@keyframes spin{to{transform:rotate(360deg)}}';
document.head.appendChild(style);

function loading(id, msg) {
  document.getElementById(id).innerHTML = `<div style="margin-top:16px;display:flex;align-items:center;gap:10px;color:#94a3b8;font-size:14px;"><div style="width:18px;height:18px;border:2px solid #374151;border-top-color:#f59e0b;border-radius:50%;animation:spin 0.8s linear infinite;flex-shrink:0;"></div>${msg}</div>`;
}

function result(id, html) {
  document.getElementById(id).innerHTML = `<div style="background:#0f172a;border:1px solid #1e3a5f;border-radius:8px;padding:16px;margin-top:16px;">${html}</div>`;
}

function txSent(id, hash) {
  result(id, `✅ Transaction sent!<br><span style="color:#a78bfa;font-size:12px;word-break:break-all;">${hash}</span><br><span style="color:#94a3b8;font-size:13px;margin-top:8px;display:block;">Finalization ~1 min. Refresh after.</span>`);
}

window.connectWallet = async function () {
  if (!window.ethereum) { alert('Please install MetaMask!'); return; }
  try {
    const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
    userAddress = accounts[0];
    readClient = createClient({ chain: studionet });
    writeClient = createClient({ chain: studionet, account: userAddress, provider: window.ethereum });
    const btn = document.getElementById('connectBtn');
    btn.textContent = userAddress.slice(0, 6) + '...' + userAddress.slice(-4);
    btn.style.background = '#052e16';
    btn.style.color = '#4ade80';
    window.loadRiddles();
  } catch (e) { alert('Error: ' + e.message); }
};

window.createRiddle = async function () {
  if (!writeClient) { alert('Connect wallet first!'); return; }
  const topic = document.getElementById('c-topic').value.trim();
  const difficulty = document.getElementById('c-difficulty').value;
  if (!topic) { alert('Enter a topic!'); return; }
  loading('create-result', 'Validators generating and checking the riddle...');
  try {
    const hash = await writeClient.writeContract({
      address: CONTRACT_ADDRESS,
      functionName: 'create_riddle',
      args: [topic, difficulty],
      value: 0n,
    });
    txSent('create-result', hash);
  } catch (e) { result('create-result', '❌ ' + e.message); }
};

window.submitAnswer = async function (riddleId) {
  if (!writeClient) { alert('Connect wallet first!'); return; }
  const player = document.getElementById('ans-player-' + riddleId).value.trim();
  const answer = document.getElementById('ans-text-' + riddleId).value.trim();
  if (!player || !answer) { alert('Enter your name and an answer!'); return; }
  const resultId = 'ans-result-' + riddleId;
  loading(resultId, 'Validators judging your answer...');
  try {
    const hash = await writeClient.writeContract({
      address: CONTRACT_ADDRESS,
      functionName: 'submit_answer',
      args: [riddleId, player, answer],
      value: 0n,
    });
    txSent(resultId, hash);
  } catch (e) { result(resultId, '❌ ' + e.message); }
};

window.loadRiddles = async function () {
  if (!readClient) readClient = createClient({ chain: studionet });
  const el = document.getElementById('riddle-list');
  el.innerHTML = '<p style="color:#94a3b8;font-size:14px;margin:0;">Loading riddles...</p>';
  try {
    const data = await readClient.readContract({ address: CONTRACT_ADDRESS, functionName: 'get_all_riddles', args: [] });
    const riddles = typeof data === 'string' ? JSON.parse(data) : data;
    const vals = Object.values(riddles).reverse();
    if (!vals.length) { el.innerHTML = '<p style="color:#4b5563;font-size:14px;margin:0;">No riddles yet. Create one above!</p>'; return; }
    el.innerHTML = vals.map(r => {
      if (!r.riddle_text) return '';
      const solvedBadge = r.solved
        ? `<span style="background:#052e16;color:#4ade80;padding:3px 12px;border-radius:20px;font-size:12px;font-weight:600;">SOLVED by ${r.solved_by}</span>`
        : `<span style="background:#1e1b2e;color:#a78bfa;padding:3px 12px;border-radius:20px;font-size:12px;font-weight:600;">OPEN</span>`;
      const answerForm = r.solved ? '' : `
        <div style="display:flex;gap:8px;margin-top:12px;">
          <input id="ans-player-${r.id}" placeholder="your name" style="background:#1f2937;border:1px solid #374151;border-radius:8px;padding:8px 12px;color:#e2e8f0;width:120px;box-sizing:border-box;font-size:13px;outline:none;" />
          <input id="ans-text-${r.id}" placeholder="your answer" style="background:#1f2937;border:1px solid #374151;border-radius:8px;padding:8px 12px;color:#e2e8f0;flex:1;box-sizing:border-box;font-size:13px;outline:none;" />
          <button onclick="window.submitAnswer('${r.id}')" style="background:#f59e0b;color:#1a1a1a;padding:8px 16px;border-radius:8px;font-weight:600;cursor:pointer;border:none;font-size:13px;white-space:nowrap;">Guess</button>
        </div>
        <div id="ans-result-${r.id}"></div>
      `;
      return `<div style="padding:14px;background:#1a1a2e;border-radius:8px;margin-bottom:10px;">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px;margin-bottom:8px;">
          <span style="font-size:11px;background:#1e1b2e;color:#f59e0b;padding:2px 8px;border-radius:4px;text-transform:uppercase;">${r.topic || ''} · ${r.difficulty || ''}</span>
          ${solvedBadge}
        </div>
        <p style="font-size:14px;color:#e2e8f0;margin:0;">${r.riddle_text}</p>
        ${answerForm}
      </div>`;
    }).join('');
  } catch (e) { el.innerHTML = '<p style="color:#f87171;font-size:14px;margin:0;">❌ ' + e.message + '</p>'; }
};

window.loadPlayer = async function () {
  if (!readClient) readClient = createClient({ chain: studionet });
  const name = document.getElementById('p-name').value.trim();
  if (!name) { alert('Enter a player name!'); return; }
  loading('player-result', 'Loading player stats...');
  try {
    const data = await readClient.readContract({ address: CONTRACT_ADDRESS, functionName: 'get_player', args: [name] });
    const p = typeof data === 'string' ? JSON.parse(data) : data;
    result('player-result', `
      <div style="display:flex;gap:24px;">
        <div><div style="font-size:24px;font-weight:700;color:#f59e0b;">${p.score ?? 0}</div><div style="font-size:12px;color:#94a3b8;">score</div></div>
        <div><div style="font-size:24px;font-weight:700;">${p.solved_count ?? 0}</div><div style="font-size:12px;color:#94a3b8;">solved</div></div>
        <div><div style="font-size:24px;font-weight:700;">${p.attempts ?? 0}</div><div style="font-size:12px;color:#94a3b8;">attempts</div></div>
      </div>
    `);
  } catch (e) { result('player-result', '❌ ' + e.message); }
};

readClient = createClient({ chain: studionet });
window.loadRiddles();
