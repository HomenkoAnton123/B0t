function showToast(msg, color = 'var(--green)') {
  let t = document.querySelector('.toast');
  if (!t) {
    t = document.createElement('div');
    t.className = 'toast';
    document.body.appendChild(t);
  }
  t.textContent = msg;
  t.style.color = color;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 2500);
}

async function completeTask(id, btn) {
  btn.disabled = true;
  btn.textContent = '...';
  const res = await fetch(`/task/${id}/complete`, { method: 'POST' });
  if (res.ok) {
    const card = btn.closest('.task-card');
    card.style.transition = 'opacity 0.3s, transform 0.3s';
    card.style.opacity = '0';
    card.style.transform = 'scale(0.95)';
    setTimeout(() => { card.remove(); updateStats(); }, 300);
    showToast('✓ ЗАДАЧА ВЫПОЛНЕНА');
  }
}

async function deleteTask(id, btn) {
  btn.disabled = true;
  const res = await fetch(`/task/${id}/delete`, { method: 'POST' });
  if (res.ok) {
    const card = btn.closest('.task-card');
    card.style.transition = 'opacity 0.3s, transform 0.3s';
    card.style.opacity = '0';
    card.style.transform = 'translateX(20px)';
    setTimeout(() => { card.remove(); updateStats(); }, 300);
    showToast('✕ УДАЛЕНО', 'var(--red)');
  }
}

async function resetReminder(id, btn) {
  btn.disabled = true;
  const res = await fetch(`/task/${id}/reset-reminder`, { method: 'POST' });
  if (res.ok) {
    btn.remove();
    showToast('↺ НАПОМИНАНИЕ СБРОШЕНО', 'var(--yellow)');
  }
}

function toggleDone(btn) {
  const grid = btn.closest('.done-section').querySelector('.done-grid');
  const hidden = grid.classList.toggle('hidden');
  btn.textContent = hidden ? '▾ ПОКАЗАТЬ' : '▴ СКРЫТЬ';
}

function updateStats() {
  const active = document.querySelectorAll('.tasks-section:not(.done-section) .task-card').length;
  const nums = document.querySelectorAll('.stat-num');
  if (nums[0]) nums[0].textContent = active;
}

// Staggered card animation on load
document.querySelectorAll('.task-card').forEach((card, i) => {
  card.style.animationDelay = `${i * 0.05}s`;
});
