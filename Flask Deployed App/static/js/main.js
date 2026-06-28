// ============================================
//   LeafMitra - Main JavaScript
// ============================================

document.addEventListener('DOMContentLoaded', function () {

  // ---- Navbar Toggle (Mobile) ----
  const toggler = document.getElementById('navbar-toggler');
  const navLinks = document.getElementById('nav-links');
  if (toggler && navLinks) {
    toggler.addEventListener('click', () => navLinks.classList.toggle('open'));
  }

  // ---- Flash Message Auto-dismiss ----
  document.querySelectorAll('.flash-alert').forEach(el => {
    const closeBtn = el.querySelector('.flash-close');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => el.remove());
    }
    setTimeout(() => {
      el.style.opacity = '0';
      el.style.transform = 'translateX(100%)';
      el.style.transition = 'all 0.4s ease';
      setTimeout(() => el.remove(), 400);
    }, 5000);
  });

  // ---- Drop Zone & File Preview ----
  const dropZone = document.getElementById('drop-zone');
  const fileInput = document.getElementById('file-input');
  const previewContainer = document.getElementById('preview-container');
  const previewImg = document.getElementById('preview-img');
  const previewRemove = document.getElementById('preview-remove');
  const uploadForm = document.getElementById('upload-form');
  const loadingOverlay = document.getElementById('loading-overlay');

  if (dropZone && fileInput) {

    // Click to open file picker
    dropZone.addEventListener('click', () => fileInput.click());

    // Drag & Drop
    dropZone.addEventListener('dragover', e => {
      e.preventDefault();
      dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));

    dropZone.addEventListener('drop', e => {
      e.preventDefault();
      dropZone.classList.remove('dragover');
      const files = e.dataTransfer.files;
      if (files.length > 0) handleFile(files[0]);
    });

    fileInput.addEventListener('change', function () {
      if (this.files.length > 0) handleFile(this.files[0]);
    });
  }

  function handleFile(file) {
    // Validate type
    const allowed = ['image/jpeg', 'image/jpg', 'image/png'];
    if (!allowed.includes(file.type)) {
      showFlash('Only JPG, JPEG, and PNG files are allowed.', 'error');
      return;
    }

    // Validate size (5MB)
    if (file.size > 5 * 1024 * 1024) {
      showFlash('File too large. Maximum size is 5MB.', 'error');
      return;
    }

    // Set file to input
    const dt = new DataTransfer();
    dt.items.add(file);
    fileInput.files = dt.files;

    // Show preview
    const reader = new FileReader();
    reader.onload = e => {
      previewImg.src = e.target.result;
      previewContainer.style.display = 'block';
      dropZone.style.display = 'none';
    };
    reader.readAsDataURL(file);
  }

  // Remove preview
  if (previewRemove) {
    previewRemove.addEventListener('click', e => {
      e.stopPropagation();
      previewContainer.style.display = 'none';
      dropZone.style.display = 'block';
      fileInput.value = '';
      previewImg.src = '#';
    });
  }

  // ---- Form Submit -> Show Loader ----
  if (uploadForm && loadingOverlay) {
    uploadForm.addEventListener('submit', function (e) {
      if (!fileInput.files || fileInput.files.length === 0) {
        e.preventDefault();
        showFlash('Please select or drop an image before submitting.', 'error');
        return;
      }
      loadingOverlay.classList.add('active');
    });
  }

  // ---- Confidence Bar Animation ----
  const confidenceFill = document.querySelector('.confidence-fill');
  if (confidenceFill) {
    const targetWidth = confidenceFill.dataset.width || '0';
    confidenceFill.style.width = '0%';
    requestAnimationFrame(() => {
      setTimeout(() => {
        confidenceFill.style.width = targetWidth + '%';
      }, 300);
    });
  }

  // ---- Render Gemini Markdown ----
  const insightsBody = document.getElementById('insights-body');
  if (insightsBody) {
    const raw = insightsBody.getAttribute('data-raw') || '';
    insightsBody.innerHTML = renderMarkdown(raw);
  }

  // ---- Camera Feature ----
  const cameraBtn = document.getElementById('camera-btn');
  if (cameraBtn) {
    let stream = null;

    cameraBtn.addEventListener('click', async () => {
      const container = document.getElementById('camera-container');
      const video = document.getElementById('camera-feed');

      if (container.style.display === 'none' || !container.style.display) {
        try {
          stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
          video.srcObject = stream;
          container.style.display = 'block';
          cameraBtn.textContent = '✕ Close Camera';
        } catch (err) {
          showFlash('Camera access denied. Please allow camera permissions.', 'error');
        }
      } else {
        if (stream) stream.getTracks().forEach(t => t.stop());
        container.style.display = 'none';
        cameraBtn.textContent = '📷 Use Camera';
      }
    });

    const captureBtn = document.getElementById('capture-btn');
    if (captureBtn) {
      captureBtn.addEventListener('click', () => {
        const video = document.getElementById('camera-feed');
        const canvas = document.createElement('canvas');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext('2d').drawImage(video, 0, 0);

        canvas.toBlob(blob => {
          const file = new File([blob], 'camera_capture.jpg', { type: 'image/jpeg' });
          handleFile(file);
          if (stream) stream.getTracks().forEach(t => t.stop());
          document.getElementById('camera-container').style.display = 'none';
          cameraBtn.textContent = '📷 Use Camera';
        }, 'image/jpeg', 0.9);
      });
    }
  }

});

// ---- Utility: Show Flash ----
function showFlash(message, type = 'error') {
  const container = document.getElementById('flash-container');
  if (!container) return;

  const alert = document.createElement('div');
  alert.className = `flash-alert flash-${type}`;
  alert.innerHTML = `
    <span>${type === 'error' ? '⚠️' : '✅'}</span>
    <span>${message}</span>
    <button class="flash-close" onclick="this.parentElement.remove()">✕</button>
  `;
  container.appendChild(alert);

  setTimeout(() => {
    alert.style.opacity = '0';
    alert.style.transform = 'translateX(100%)';
    alert.style.transition = 'all 0.4s ease';
    setTimeout(() => alert.remove(), 400);
  }, 5000);
}

// ---- Utility: Simple Markdown Renderer ----
function renderMarkdown(text) {
  if (!text) return '';

  return text
    // Bold: **text**
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    // Headers: **1. Title** or lines starting with #
    .replace(/^#{1,4}\s+(.+)$/gm, '<h4>$1</h4>')
    // Bullet points
    .replace(/^[•\-\*]\s+(.+)$/gm, '<li>$1</li>')
    // Numbered list
    .replace(/^\d+\.\s+(.+)$/gm, '<li>$1</li>')
    // Wrap consecutive <li> in <ul>
    .replace(/(<li>.*<\/li>(\n|$))+/g, match => `<ul>${match}</ul>`)
    // Paragraphs (blank line separated)
    .replace(/\n{2,}/g, '</p><p>')
    // Wrap in paragraph
    .replace(/^(?!<[hul])(.+)$/gm, (m) => m.startsWith('<') ? m : `<p>${m}</p>`)
    // Clean up empty paragraphs
    .replace(/<p><\/p>/g, '')
    .replace(/<p>\s*<\/p>/g, '');
}
