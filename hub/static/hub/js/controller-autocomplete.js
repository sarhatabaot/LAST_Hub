/**
 * Brigadier-style command completer for the controller page.
 *
 * On every keystroke / cursor move the input is tokenised: the cursor is
 * either in *command-name* phase (no '(' yet, or before the first one) or
 * in *arg N* phase (inside parens, between commas at depth 0).
 *
 * In each phase we hand Awesomplete a different list of suggestions and a
 * matching hint. Filter and replace operate on the *current token* only,
 * so picking a suggestion swaps just the slot under the cursor instead of
 * blowing away the rest of the input.
 */
(function () {
  function init(root) {
    const inputs = (root || document).querySelectorAll(
      'input[data-controller-autocomplete]'
    );
    inputs.forEach(setupOne);
  }

  function setupOne(input) {
    if (input._brigadier) return;

    const dataEl = document.getElementById('controller-command-schema');
    if (!dataEl) return;

    let schema;
    try {
      schema = JSON.parse(dataEl.textContent);
    } catch (e) {
      return;
    }

    const byBase = Object.create(null);
    schema.forEach((entry) => { byBase[entry.base] = entry; });
    const commandList = schema.map((entry) => ({
      label: entry.base + ' — ' + entry.summary,
      value: entry.base,
    }));

    const hintEl = (input.closest('form') || document)
      .querySelector('[data-controller-hint]');

    function analyze() {
      const text = input.value;
      const cursor = input.selectionStart || 0;
      const open = text.indexOf('(');
      if (open < 0 || cursor <= open) {
        return { phase: 'command', tokenStart: 0, tokenEnd: cursor };
      }
      const command = text.slice(0, open).trim();
      let depth = 0;
      let argIndex = 0;
      let argStart = open + 1;
      for (let i = open + 1; i < cursor; i++) {
        const ch = text[i];
        if (ch === '[' || ch === '(' || ch === '{') depth++;
        else if (ch === ']' || ch === ')' || ch === '}') depth--;
        else if (ch === ',' && depth === 0) {
          argIndex++;
          argStart = i + 1;
        }
      }
      while (argStart < cursor && /\s/.test(text[argStart])) argStart++;
      return {
        phase: 'arg',
        command: command,
        argIndex: argIndex,
        tokenStart: argStart,
        tokenEnd: cursor,
      };
    }

    const ac = new Awesomplete(input, {
      list: commandList,
      minChars: 0,
      autoFirst: false,
      sort: false,
      filter: function (suggestion) {
        const ctx = analyze();
        const token = input.value
          .slice(ctx.tokenStart, ctx.tokenEnd)
          .toLowerCase();
        if (!token) return true;
        const haystack = (suggestion.label || suggestion.value).toLowerCase();
        return haystack.indexOf(token) !== -1;
      },
      replace: function (suggestion) {
        const ctx = analyze();
        const text = input.value;
        let value = suggestion.value;
        if (ctx.phase === 'command') {
          const spec = byBase[value];
          if (spec && spec.args && spec.args.length > 0) value = value + '(';
        }
        input.value = text.slice(0, ctx.tokenStart) + value + text.slice(ctx.tokenEnd);
        const newCursor = ctx.tokenStart + value.length;
        input.setSelectionRange(newCursor, newCursor);
        // Recompute phase + suggestions for the next slot.
        setTimeout(() => {
          input.dispatchEvent(new Event('input', { bubbles: true }));
        }, 0);
      },
    });

    function setHint(state, fragments) {
      if (!hintEl) return;
      hintEl.textContent = '';
      hintEl.dataset.state = state || '';
      fragments.forEach((node) => {
        if (typeof node === 'string') {
          hintEl.appendChild(document.createTextNode(node));
        } else {
          hintEl.appendChild(node);
        }
      });
    }

    function el(tag, className, text) {
      const node = document.createElement(tag);
      if (className) node.className = className;
      if (text != null) node.textContent = text;
      return node;
    }

    function update() {
      const ctx = analyze();
      if (ctx.phase === 'command') {
        ac.list = commandList;
        setHint('', ['Pick a command — type to filter.']);
        ac.evaluate();
        return;
      }
      const spec = byBase[ctx.command];
      if (!spec) {
        ac.list = [];
        setHint('error', ['Unknown command: ' + ctx.command]);
        ac.close();
        return;
      }
      const arg = spec.args[ctx.argIndex];
      if (!arg) {
        ac.list = [];
        if (spec.args.length === 0) {
          setHint('warn', [spec.base + ' takes no arguments.']);
        } else {
          setHint('warn', [
            spec.base + ': extra argument (expected ' + spec.args.length + ').',
          ]);
        }
        ac.close();
        return;
      }
      ac.list = (arg.suggestions || []).map((s) => ({ label: s, value: s }));
      const fragments = [
        'arg ' + (ctx.argIndex + 1) + '/' + spec.args.length + ': ',
        el('span', 'arg-name', arg.name),
        ' — ' + (arg.summary || ''),
      ];
      if (arg.example) {
        fragments.push(' ');
        fragments.push(el('span', 'arg-example', 'e.g. ' + arg.example));
      }
      setHint('', fragments);
      ac.evaluate();
    }

    input.addEventListener('input', update);
    input.addEventListener('keyup', update);
    input.addEventListener('click', update);
    input.addEventListener('focus', update);

    input._brigadier = ac;
    update();
  }

  document.addEventListener('DOMContentLoaded', () => init(document));
  document.body.addEventListener('htmx:afterSwap', (ev) => init(ev.detail.target));
})();
