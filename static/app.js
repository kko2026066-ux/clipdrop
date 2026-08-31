const urlInput = document.querySelector('#url');
const clearButton = document.querySelector('#clear-url');
const downloadButton = document.querySelector('#download-btn');
const errorMessage = document.querySelector('#form-error');
const progressPanel = document.querySelector('#progress-panel');
const progressBar = document.querySelector('#progress-bar');
const progressMessage = document.querySelector('#progress-message');
const progressValue = document.querySelector('#progress-value');
const resultPanel = document.querySelector('#result-panel');
const resultTitle = document.querySelector('#result-title');
const resultMessage = document.querySelector('#result-message');
const saveButton = document.querySelector('#save-btn');

urlInput.addEventListener('input', () => {
  clearButton.classList.toggle('visible', Boolean(urlInput.value));
  errorMessage.textContent = '';
});

clearButton.addEventListener('click', () => {
  urlInput.value = '';
  urlInput.focus();
  clearButton.classList.remove('visible');
});

document.querySelectorAll('input[name="format"]').forEach((input) => {
  input.addEventListener('change', () => {
    document.querySelectorAll('.format-option').forEach((option) => option.classList.remove('active'));
    input.closest('.format-option').classList.add('active');
  });
});

function setProgress(progress, message) {
  const value = Math.max(0, Math.min(100, Number(progress) || 0));
  progressBar.style.width = `${value}%`;
  progressValue.textContent = `${Math.round(value)}%`;
  progressMessage.textContent = message || '다운로드 중…';
}

async function pollJob(jobId) {
  const response = await fetch(`/api/download/${jobId}`);
  const job = await response.json();
  if (!response.ok) throw new Error(job.error || '작업 상태를 확인할 수 없습니다.');
  setProgress(job.progress, job.message);

  if (job.status === 'complete') {
    progressPanel.classList.add('hidden');
    resultTitle.textContent = job.title || '다운로드 완료';
    resultMessage.textContent = job.message;
    saveButton.href = job.download_url;
    resultPanel.classList.remove('hidden');
    downloadButton.disabled = false;
    downloadButton.querySelector('span').textContent = '다시 다운로드';
    return;
  }
  if (job.status === 'error') throw new Error(job.message);
  window.setTimeout(() => pollJob(jobId).catch(handleError), 900);
}

function handleError(error) {
  progressPanel.classList.add('hidden');
  resultPanel.classList.add('hidden');
  errorMessage.textContent = error.message;
  downloadButton.disabled = false;
  downloadButton.querySelector('span').textContent = '다운로드';
}

downloadButton.addEventListener('click', async () => {
  const url = urlInput.value.trim();
  if (!url) {
    errorMessage.textContent = 'YouTube URL을 입력해주세요.';
    urlInput.focus();
    return;
  }
  if (!/^https?:\/\//i.test(url)) {
    errorMessage.textContent = '올바른 URL을 입력해주세요.';
    urlInput.focus();
    return;
  }

  downloadButton.disabled = true;
  downloadButton.querySelector('span').textContent = '준비 중…';
  errorMessage.textContent = '';
  resultPanel.classList.add('hidden');
  progressPanel.classList.remove('hidden');
  setProgress(0, '다운로드를 준비하고 있습니다…');

  try {
    const format = document.querySelector('input[name="format"]:checked').value;
    const response = await fetch('/api/download', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url, audio_only: format === 'audio' }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || '다운로드를 시작할 수 없습니다.');
    await pollJob(data.job_id);
  } catch (error) {
    handleError(error);
  }
});

urlInput.addEventListener('keydown', (event) => {
  if (event.key === 'Enter') downloadButton.click();
});
