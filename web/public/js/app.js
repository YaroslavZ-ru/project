(function () {
  'use strict';

  // ==================== Состояние ====================
  let lastResult = null;
  let selectedRating = 0;
  let currentTerm = '';

  // ==================== Инициализация ====================
  document.addEventListener('DOMContentLoaded', () => {
    setupHints();
    setupStarRating();
    checkHealth();
    loadStats();
  });

  // ==================== Динамические подсказки ====================
  function setupHints() {
    const container = document.getElementById('hintsContainer');
    container.addEventListener('input', (e) => {
      if (!e.target.classList.contains('hint-input')) return;
      const inputs = container.querySelectorAll('.hint-input');
      const filledCount = Array.from(inputs).filter(i => i.value.trim()).length;

      if (filledCount === inputs.length && inputs.length < 3) {
        addHintField(container, inputs.length + 1);
      }
    });
  }

  function addHintField(container, num) {
    if (num > 3) return;
    const div = document.createElement('div');
    div.className = 'form-group hint-row';
    div.innerHTML = '<label>Подсказка ' + num + '</label>' +
      '<input type="text" class="hint-input" placeholder="Подсказка ' + num + '" maxlength="50" autocomplete="off">';
    container.appendChild(div);
    div.querySelector('input').focus();
  }

  // ==================== Звёздный рейтинг ====================
  function setupStarRating() {
    const stars = document.querySelectorAll('#starRating .star');
    stars.forEach(star => {
      star.addEventListener('click', () => {
        selectedRating = parseInt(star.dataset.value);
        stars.forEach(s => {
          s.classList.toggle('active', parseInt(s.dataset.value) <= selectedRating);
        });
      });
      star.addEventListener('mouseenter', () => {
        const val = parseInt(star.dataset.value);
        stars.forEach(s => {
          s.classList.toggle('active', parseInt(s.dataset.value) <= val);
        });
      });
      star.addEventListener('mouseleave', () => {
        stars.forEach(s => {
          s.classList.toggle('active', parseInt(s.dataset.value) <= selectedRating);
        });
      });
    });
  }

  // ==================== Анализ ====================
  window.analyze = async function () {
    const termInput = document.getElementById('termInput');
    const term = termInput.value.trim();
    if (!term) {
      termInput.focus();
      return;
    }

    const hints = Array.from(document.querySelectorAll('.hint-input'))
      .map(i => i.value.trim())
      .filter(Boolean)
      .slice(0, 3);

    const debug = document.getElementById('debugToggle').checked;
    const btn = document.getElementById('analyzeBtn');

    btn.disabled = true;
    btn.textContent = 'Анализ...';
    currentTerm = term;

    try {
      const res = await fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ term, hints, debug }),
      });
      const data = await res.json();
      lastResult = data;
      renderResult(data);
    } catch (err) {
      renderError('Ошибка соединения с сервером: ' + err.message);
    } finally {
      btn.disabled = false;
      btn.textContent = 'Анализировать';
    }
  };

  // Enter в поле термина
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && document.activeElement.id === 'termInput') {
      analyze();
    }
  });

  // ==================== Рендер результата ====================
  function renderResult(data) {
    const section = document.getElementById('resultSection');
    section.style.display = '';

    // Статус
    const statusEl = document.getElementById('resultStatus');
    statusEl.className = 'result-status ' + data.status;
    const statusLabels = { ok: 'Успешно', ambiguous: 'Многозначность', error: 'Ошибка' };
    statusEl.textContent = statusLabels[data.status] || data.status;

    // Сброс блоков
    document.getElementById('ambiguousBlock').style.display = 'none';
    document.getElementById('domainBlock').style.display = 'none';
    document.getElementById('parametersBlock').style.display = 'none';
    document.getElementById('warningsBlock').style.display = 'none';
    document.getElementById('refinementsBlock').style.display = 'none';
    document.getElementById('debugBlock').style.display = 'none';
    document.getElementById('feedbackSection').style.display = 'none';
    document.getElementById('exportSection').style.display = 'none';

    if (data.status === 'error') {
      renderError(data.message || 'Неизвестная ошибка');
      return;
    }

    // Ambiguous — показать кандидатов
    if (data.status === 'ambiguous') {
      document.getElementById('ambiguousBlock').style.display = '';
      const container = document.getElementById('domainCandidates');
      container.innerHTML = '';
      const candidates = (data.selected_context && data.selected_context.domain_candidates) || [];
      candidates.forEach(c => {
        const div = document.createElement('div');
        div.className = 'domain-candidate';
        div.innerHTML =
          '<div class="domain-candidate-name">' + escapeHtml(c.domain) + '</div>' +
          '<div class="domain-candidate-info">' +
          'Уверенность: ' + (c.confidence * 100).toFixed(0) + '%' +
          (c.example_term ? ' | Пример: ' + escapeHtml(c.example_term) : '') +
          '</div>';
        div.addEventListener('click', () => selectDomain(c.domain));
        container.appendChild(div);
      });
      showWarnings(data.warnings);
      showRefinements(data.suggested_refinements);
      showDebug(data);
      document.getElementById('exportSection').style.display = '';
      return;
    }

    // OK — показать домен и параметры
    if (data.selected_context && data.selected_context.domain) {
      document.getElementById('domainBlock').style.display = '';
      document.getElementById('domainValue').textContent = data.selected_context.domain;
      const conf = data.selected_context.confidence;
      document.getElementById('confidenceBadge').textContent =
        conf != null ? 'Уверенность: ' + (conf * 100).toFixed(0) + '%' : '';
    }

    // Параметры
    if (data.parameters && data.parameters.length > 0) {
      document.getElementById('parametersBlock').style.display = '';
      const tbody = document.getElementById('paramsBody');
      tbody.innerHTML = '';
      data.parameters.forEach(p => {
        const tr = document.createElement('tr');
        const confPct = p.confidence != null ? (p.confidence * 100).toFixed(0) : '—';
        const barWidth = p.confidence != null ? (p.confidence * 60) : 0;
        tr.innerHTML =
          '<td><strong>' + escapeHtml(p.label_ru || p.name) + '</strong><br><small style="color:var(--text-muted)">' + escapeHtml(p.name) + '</small></td>' +
          '<td>' + escapeHtml(p.type) + '</td>' +
          '<td>' + escapeHtml(p.description || '—') + '</td>' +
          '<td>' + escapeHtml(p.unit || '—') + '</td>' +
          '<td><span class="confidence-bar" style="width:' + barWidth + 'px"></span>' + confPct + '%</td>';
        tbody.appendChild(tr);
      });
    }

    showWarnings(data.warnings);
    showRefinements(data.suggested_refinements);
    showDebug(data);

    // Показать.feedback и экспорт
    document.getElementById('feedbackSection').style.display = '';
    document.getElementById('exportSection').style.display = '';
    selectedRating = 0;
    document.querySelectorAll('#starRating .star').forEach(s => s.classList.remove('active'));
    document.getElementById('commentInput').value = '';
    document.getElementById('feedbackMsg').textContent = '';
  }

  function renderError(message) {
    const section = document.getElementById('resultSection');
    section.style.display = '';
    document.getElementById('resultStatus').className = 'result-status error';
    document.getElementById('resultStatus').textContent = 'Ошибка: ' + message;
  }

  function showWarnings(warnings) {
    const block = document.getElementById('warningsBlock');
    const list = document.getElementById('warningsList');
    if (!warnings || warnings.length === 0) { block.style.display = 'none'; return; }
    block.style.display = '';
    list.innerHTML = '';
    warnings.forEach(w => {
      const li = document.createElement('li');
      li.textContent = w;
      list.appendChild(li);
    });
  }

  function showRefinements(refinements) {
    const block = document.getElementById('refinementsBlock');
    const list = document.getElementById('refinementsList');
    if (!refinements || refinements.length === 0) { block.style.display = 'none'; return; }
    block.style.display = '';
    list.innerHTML = '';
    refinements.forEach(r => {
      const li = document.createElement('li');
      li.textContent = r;
      list.appendChild(li);
    });
  }

  function showDebug(data) {
    const block = document.getElementById('debugBlock');
    if (!data.debug_info && !data.trace) { block.style.display = 'none'; return; }
    block.style.display = '';
    const content = {};
    if (data.debug_info) content.debug_info = data.debug_info;
    if (data.trace) content.trace = data.trace;
    document.getElementById('debugContent').textContent = JSON.stringify(content, null, 2);
  }

  // ==================== Выбор домена (ambiguous) ====================
  async function selectDomain(domain) {
    const term = currentTerm;
    const hints = Array.from(document.querySelectorAll('.hint-input'))
      .map(i => i.value.trim())
      .filter(Boolean)
      .slice(0, 3);
    const debug = document.getElementById('debugToggle').checked;
    const btn = document.getElementById('analyzeBtn');

    btn.disabled = true;
    btn.textContent = 'Анализ...';

    try {
      const res = await fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ term, hints, debug, selected_domain: domain }),
      });
      const data = await res.json();
      lastResult = data;
      renderResult(data);
    } catch (err) {
      renderError('Ошибка: ' + err.message);
    } finally {
      btn.disabled = false;
      btn.textContent = 'Анализировать';
    }
  }

  // ==================== Экспорт ====================
  window.exportJSON = function () {
    if (!lastResult) return;
    download(JSON.stringify(lastResult, null, 2), 'ai-terminator-result.json', 'application/json');
  };

  window.exportCSV = function () {
    if (!lastResult || !lastResult.parameters) return;
    const rows = [['name', 'label_ru', 'type', 'description', 'unit', 'confidence']];
    lastResult.parameters.forEach(p => {
      rows.push([
        csvEscape(p.name),
        csvEscape(p.label_ru || ''),
        csvEscape(p.type),
        csvEscape(p.description || ''),
        csvEscape(p.unit || ''),
        p.confidence != null ? p.confidence.toFixed(2) : '',
      ]);
    });
    download(rows.map(r => r.join(',')).join('\n'), 'ai-terminator-result.csv', 'text/csv');
  };

  window.exportTXT = function () {
    if (!lastResult) return;
    const lines = [];
    lines.push('AI-Terminator — Результат анализа');
    lines.push('='.repeat(40));
    lines.push('Термин: ' + (lastResult.term || '—'));
    if (lastResult.selected_context && lastResult.selected_context.domain) {
      lines.push('Домен: ' + lastResult.selected_context.domain);
      if (lastResult.selected_context.confidence != null) {
        lines.push('Уверенность: ' + (lastResult.selected_context.confidence * 100).toFixed(0) + '%');
      }
    }
    lines.push('');
    if (lastResult.parameters && lastResult.parameters.length > 0) {
      lines.push('Параметры:');
      lines.push('-'.repeat(40));
      lastResult.parameters.forEach((p, i) => {
        lines.push('');
        lines.push((i + 1) + '. ' + (p.label_ru || p.name) + ' (' + p.name + ')');
        lines.push('   Тип: ' + p.type);
        if (p.description) lines.push('   Описание: ' + p.description);
        if (p.unit) lines.push('   Ед. измерения: ' + p.unit);
        if (p.confidence != null) lines.push('   Уверенность: ' + (p.confidence * 100).toFixed(0) + '%');
      });
    }
    if (lastResult.warnings && lastResult.warnings.length > 0) {
      lines.push('');
      lines.push('Предупреждения:');
      lastResult.warnings.forEach(w => lines.push('  - ' + w));
    }
    if (lastResult.suggested_refinements && lastResult.suggested_refinements.length > 0) {
      lines.push('');
      lines.push('Рекомендации:');
      lastResult.suggested_refinements.forEach(r => lines.push('  - ' + r));
    }
    lines.push('');
    lines.push('='.repeat(40));
    lines.push('Сгенерировано AI-Terminator Web');
    download(lines.join('\n'), 'ai-terminator-result.txt', 'text/plain');
  };

  function csvEscape(val) {
    if (typeof val !== 'string') return String(val);
    if (val.includes(',') || val.includes('"') || val.includes('\n')) {
      return '"' + val.replace(/"/g, '""') + '"';
    }
    return val;
  }

  function download(content, filename, mime) {
    const blob = new Blob([content], { type: mime + ';charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  // ==================== Обратная связь ====================
  window.submitFeedback = async function () {
    if (!selectedRating || !lastResult) return;
    const comment = document.getElementById('commentInput').value.trim();

    try {
      const res = await fetch('/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          term: currentTerm,
          rating: selectedRating,
          comment: comment || null,
          concept_id: lastResult.selected_context ? lastResult.selected_context.concept_id : null,
        }),
      });
      const data = await res.json();
      document.getElementById('feedbackMsg').textContent = 'Спасибо за оценку!';
      setTimeout(() => { document.getElementById('feedbackMsg').textContent = ''; }, 3000);
    } catch (err) {
      document.getElementById('feedbackMsg').textContent = 'Ошибка отправки';
    }
  };

  // ==================== Здоровье API ====================
  async function checkHealth() {
    const dot = document.getElementById('statusDot');
    const text = document.getElementById('statusText');
    try {
      const res = await fetch('/api/health');
      const data = await res.json();
      if (data.status === 'ok') {
        dot.className = 'status-dot online';
        text.textContent = 'API доступен';
      } else {
        dot.className = 'status-dot offline';
        text.textContent = 'API: ' + (data.status || 'неизвестно');
      }
    } catch {
      dot.className = 'status-dot offline';
      text.textContent = 'API недоступен';
    }
  }

  // ==================== Статистика ====================
  async function loadStats() {
    try {
      const res = await fetch('/api/stats');
      const data = await res.json();
      document.getElementById('statConcepts').textContent = data.concepts_count || '—';
      document.getElementById('statParams').textContent = data.parameters_count || '—';
    } catch {
      document.getElementById('statConcepts').textContent = '—';
      document.getElementById('statParams').textContent = '—';
    }
    try {
      const res = await fetch('/api/health');
      const data = await res.json();
      document.getElementById('statModel').textContent = data.model_loaded ? 'Загружена' : 'Не загружена';
    } catch {
      document.getElementById('statModel').textContent = '—';
    }
  }

  // ==================== Утилиты ====================
  function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

})();
