// static/script.js

function showMessage(message, isError = false) {
    const errorDiv = document.getElementById('error-message');
    errorDiv.textContent = message;
    errorDiv.classList.remove('hidden');
    if (isError) {
        errorDiv.style.backgroundColor = '#ff3b3b'; 
    } else {
        errorDiv.style.backgroundColor = '#4CAF50'; 
    }
    setTimeout(() => {
        errorDiv.classList.add('hidden');
    }, 5000);
}

async function getFormats() {
    const urlInput = document.getElementById('youtubeUrl');
    const url = urlInput.value.trim();
    const loadingDiv = document.getElementById('loading');
    const resultsDiv = document.getElementById('results');
    const videoInfoDiv = document.getElementById('videoInfo');
    const downloadOptionsDiv = document.getElementById('downloadOptions');

    resultsDiv.classList.add('hidden');
    videoInfoDiv.innerHTML = '';
    downloadOptionsDiv.innerHTML = '';
    document.getElementById('error-message').classList.add('hidden');
    
    if (!url) {
        showMessage('براہ کرم یوٹیوب لنک درج کریں۔', true);
        return;
    }

    loadingDiv.classList.remove('hidden');

    try {
        const response = await fetch('/get_formats', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: url })
        });

        const data = await response.json();
        loadingDiv.classList.add('hidden');

        if (response.ok) {
            resultsDiv.classList.remove('hidden');

            const infoHTML = `
                <img src="${data.thumbnail}" alt="Video Thumbnail">
                <div>
                    <h3>ویڈیو کا عنوان:</h3>
                    <p>${data.title}</p>
                </div>
            `;
            videoInfoDiv.innerHTML = infoHTML;
            
            data.formats.forEach(format => {
                let qualityClass = '';
                if (format.quality.includes('MP3')) {
                    qualityClass = 'mp3';
                } else if (parseInt(format.quality.replace('p', '')) >= 1080) {
                    qualityClass = 'high-res';
                } else {
                    qualityClass = 'hd';
                }

                const itemHTML = `
                    <div class="download-item">
                        <p class="quality-label ${qualityClass}">${format.quality}</p>
                        <small>فارمیٹ: ${format.ext}</small>
                        <button onclick="startDownload('${format.format_id}', '${format.quality}')">
                            ڈاؤن لوڈ کریں
                        </button>
                    </div>
                `;
                downloadOptionsDiv.innerHTML += itemHTML;
            });

        } else {
            showMessage(`ایرَر: ${data.error || 'فارمیٹ حاصل نہیں ہو سکا۔'}`, true);
        }

    } catch (error) {
        loadingDiv.classList.add('hidden');
        showMessage('سرور سے رابطہ نہیں ہو سکا۔ (Python Server چل رہا ہے یقینی بنائیں)', true);
        console.error('Fetch error:', error);
    }
}


async function startDownload(formatId, quality) {
    const videoUrl = document.getElementById('youtubeUrl').value.trim();
    
    if (!videoUrl) {
        showMessage('براہ کرم پہلے URL درج کریں۔', true);
        return;
    }

    showMessage(`ڈاؤن لوڈ شروع ہو رہا ہے: ${quality} - براہ کرم انتظار کریں۔`, false);
    
    const downloadButton = event.currentTarget;
    downloadButton.disabled = true;
    downloadButton.textContent = 'ڈاؤن لوڈ ہو رہا ہے...';

    try {
        const response = await fetch('/download', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                url: videoUrl, 
                format_id: formatId,
                quality: quality 
            })
        });
        
        if (response.ok) {
            const blob = await response.blob();
            
            // فائل کا نام response header سے حاصل کریں
            const contentDisposition = response.headers.get('Content-Disposition');
            let filename = `download_${quality}.${formatId.includes('audio') ? 'mp3' : 'mp4'}`;
            
            if (contentDisposition && contentDisposition.indexOf('attachment') !== -1) {
                const filenameMatch = contentDisposition.match(/filename\*?=['"]?([^'"]*)['"]?/i);
                if (filenameMatch && filenameMatch[1]) {
                    filename = decodeURIComponent(filenameMatch[1].replace(/\"/g, ''));
                }
            }

            // ڈاؤن لوڈ متحرک کریں
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            a.remove();
            
            showMessage('ڈاؤن لوڈ کامیابی سے شروع ہو گئی ہے۔', false);

        } else {
            const errorData = await response.json();
            showMessage(`ڈاؤن لوڈ فیل ہوا: ${errorData.error || 'نا معلوم ایرر'}`, true);
        }
        
    } catch (error) {
        showMessage('ڈاؤن لوڈ کے عمل میں ایک غیر متوقع ایرر پیش آیا۔', true);
        console.error('Download error:', error);
    } finally {
        downloadButton.disabled = false;
        downloadButton.textContent = 'ڈاؤن لوڈ کریں';
    }
}