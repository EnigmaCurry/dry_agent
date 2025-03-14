document.addEventListener('DOMContentLoaded', () => {
  document.body.addEventListener('htmx:beforeRequest', function (evt) {
    const btn = evt.target.closest('.command-btn');
    if (btn) {
      const outputId = btn.dataset.outputId;
      const output = document.getElementById(outputId);
      const clearBtn = document.querySelector(`.clear-btn[data-output-id="${outputId}"]`);

      btn.disabled = true;

      if (output) {
        output.classList.remove('is-hidden');
        output.classList.add('fade-in');
        output.textContent = '🔄 Running...';
      }

      if (clearBtn) {
        clearBtn.classList.remove('is-hidden');
      }
    }
  });

  document.body.addEventListener('htmx:afterRequest', function (evt) {
    const btn = evt.target.closest('.command-btn');
    if (btn) btn.disabled = false;
  });

  document.body.addEventListener('htmx:responseError', function (evt) {
    const btn = evt.target.closest('.command-btn');
    if (btn) {
      const outputId = btn.dataset.outputId;
      const output = document.getElementById(outputId);
      const clearBtn = document.querySelector(`.clear-btn[data-output-id="${outputId}"]`);

      if (output) {
        output.classList.remove('is-hidden');
        output.classList.add('fade-in');
        output.textContent = evt.detail.xhr.responseText;
      }

      if (clearBtn) {
        clearBtn.classList.remove('is-hidden');
      }
    }
  });

  // 🧽 Clear button logic
  document.body.addEventListener('click', function (evt) {
    const clearBtn = evt.target.closest('.clear-btn');
    if (clearBtn) {
      const outputId = clearBtn.dataset.outputId;
      const output = document.getElementById(outputId);

      if (output) {
        output.textContent = '';
        output.classList.add('is-hidden');
      }

      clearBtn.classList.add('is-hidden');
    }
  });
});
