const form = document.getElementById('docForm');
const fileInput = document.getElementById('fileInput');
const statusEl = document.getElementById('status');
const responseEl = document.getElementById('responseText');
const charCountEl = document.getElementById('charCount');
const audioWrapper = document.getElementById('audioWrapper');
const audioPlayer = document.getElementById('audioPlayer');
const downloadLink = document.getElementById('downloadLink');

const toReadableError = (data) => {
    if (data?.message) return data.message;
    if (typeof data === 'string') return data;
    return 'Something went wrong while processing the document.';
};

form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!fileInput.files.length) {
        statusEl.textContent = 'Please choose a file before submitting.';
        return;
    }

    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append('file', file);

    statusEl.textContent = 'Processing file… this may take a moment.';
    form.querySelector('button').disabled = true;

    try {
        const response = await fetch('/process', { method: 'POST', body: formData });
        const payload = await response.json();

        if (!response.ok) {
            throw new Error(toReadableError(payload));
        }

        responseEl.textContent = payload.response || 'Processing completed with no readable text.';
        const length = payload.response ? payload.response.length : 0;
        if (length > 0) {
            charCountEl.hidden = false;
            charCountEl.textContent = `${length.toLocaleString()} chars`;
        } else {
            charCountEl.hidden = true;
        }

        const audioPath = resolveAudioPath(payload.audio, file.name);
        if (audioPath) {
            audioWrapper.hidden = false;
            audioPlayer.src = `${audioPath}?t=${Date.now()}`;
            downloadLink.hidden = false;
            downloadLink.href = audioPath;
            downloadLink.download = `${stripExtension(file.name)}.wav`;
        } else {
            audioWrapper.hidden = true;
        }

        statusEl.textContent = 'Finished processing.';
    } catch (error) {
        statusEl.textContent = error.message || 'Failed to process the document.';
        responseEl.textContent = '';
        audioWrapper.hidden = true;
        charCountEl.hidden = true;
    } finally {
        form.querySelector('button').disabled = false;
    }
});

function stripExtension(name) {
    return name.replace(/\.[^.]+$/, '');
}

function resolveAudioPath(apiAudioPath, originalFileName) {
    if (apiAudioPath) {
        if (apiAudioPath.startsWith('http')) return apiAudioPath;
        return apiAudioPath.startsWith('/') ? apiAudioPath : `/${apiAudioPath}`;
    }
    if (!originalFileName) return '';
    const cleaned = encodeURIComponent(stripExtension(originalFileName));
    return `/outputs/${cleaned}.wav`;
}
