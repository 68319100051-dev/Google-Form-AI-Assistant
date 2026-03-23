document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const step1Form = document.getElementById('step1Form');
    const step2Container = document.getElementById('step2Container');
    const statusContainer = document.getElementById('statusContainer');
    const loader = document.getElementById('loader');
    const loaderText = document.getElementById('loaderText');
    const resultBox = document.getElementById('resultBox');
    const resultIcon = document.getElementById('resultIcon');
    const resultTitle = document.getElementById('resultTitle');
    const resultMessage = document.getElementById('resultMessage');
    
    const formTitle = document.getElementById('formTitle');
    const formDescription = document.getElementById('formDescription');
    
    const scanBtn = document.getElementById('scanBtn');
    const startFillBtn = document.getElementById('startFillBtn');
    const backBtn = document.getElementById('backBtn');
    const resetBtn = document.getElementById('resetBtn');

    // Activity Feed elements
    const activityPanel = document.getElementById('activityPanel');
    const activityFeed = document.getElementById('activityFeed');

    // Settings Modal Elements
    const settingsBtn = document.getElementById('settingsBtn');
    const settingsModal = document.getElementById('settingsModal');
    const closeSettings = document.getElementById('closeSettings');
    const saveSettings = document.getElementById('saveSettings');
    const clearSettings = document.getElementById('clearSettings');
    const userGeminiKey = document.getElementById('userGeminiKey');
    const userGroqKey = document.getElementById('userGroqKey');
    const toast = document.getElementById('toast');
    const tabItems = document.querySelectorAll('.tab-item');
    const tabContents = document.querySelectorAll('.tab-content');

    let currentUrl = "";
    let currentEmail = "";
    let eventSource = null;

    // Helper: Add log
    const appendLog = (message, type = 'info') => {
        const logEl = document.createElement('div');
        logEl.className = `activity-log ${type}`;
        
        let iconHtml = '';
        if (type === 'success') iconHtml = '<i class="ph-fill ph-check-circle" style="margin-right:4px;"></i> ';
        else if (type === 'error') iconHtml = '<i class="ph-fill ph-warning-circle" style="margin-right:4px;"></i> ';
        
        logEl.innerHTML = `${iconHtml}${message}`;
        activityFeed.appendChild(logEl);
        
        // Auto scroll to bottom
        activityFeed.scrollTop = activityFeed.scrollHeight;
    };

    // Helper: Show loader
    const showLoader = (text) => {
        loaderText.textContent = text;
        statusContainer.classList.remove('hidden');
        loader.classList.remove('hidden');
        resultBox.classList.add('hidden');
    };

    // Helper: Hide loader
    const hideLoader = () => {
        loader.classList.add('hidden');
    };

    // Start SSE function
    const startSSE = () => {
        if (eventSource) eventSource.close();
        
        eventSource = new EventSource('/api/stream');
        eventSource.onmessage = (e) => {
            try {
                const data = JSON.parse(e.data);
                
                if (data.type === 'info') {
                    appendLog(data.content);
                } else if (data.type === 'error') {
                    appendLog(data.content, 'error');
                } else if (data.type === 'done') {
                    if (data.content.success) {
                        appendLog(data.content.message, 'success');
                    } else {
                        appendLog(data.content.message, 'error');
                    }
                    if (eventSource) {
                        eventSource.close();
                    }
                }
            } catch (err) {
                console.error("Parse error SSE:", err);
            }
        };
        
        eventSource.onerror = (e) => {
            console.error("SSE Error:", e);
        };
    };

    // Settings Management
    const loadSettings = () => {
        userGeminiKey.value = localStorage.getItem('user_ai_gemini_key') || '';
        userGroqKey.value = localStorage.getItem('user_ai_groq_key') || '';
    };

    const showToast = (message) => {
        toast.textContent = message;
        toast.classList.remove('hidden');
        setTimeout(() => toast.classList.add('hidden'), 3000);
    };

    settingsBtn.addEventListener('click', () => {
        loadSettings();
        settingsModal.classList.remove('hidden');
    });

    closeSettings.addEventListener('click', () => {
        settingsModal.classList.add('hidden');
    });

    saveSettings.addEventListener('click', () => {
        localStorage.setItem('user_ai_gemini_key', userGeminiKey.value.trim());
        localStorage.setItem('user_ai_groq_key', userGroqKey.value.trim());
        settingsModal.classList.add('hidden');
        showToast('บันทึกการตั้งค่าเรียบร้อยแล้ว ✅');
    });

    clearSettings.addEventListener('click', () => {
        if (confirm('ต้องการล้างข้อมูลคีย์ทั้งหมดใช่หรือไม่?')) {
            localStorage.removeItem('user_ai_gemini_key');
            localStorage.removeItem('user_ai_groq_key');
            userGeminiKey.value = '';
            userGroqKey.value = '';
            showToast('ล้างข้อมูลเรียบร้อยแล้ว');
        }
    });

    // Tab Logic
    tabItems.forEach(tab => {
        tab.addEventListener('click', () => {
            tabItems.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            const target = tab.dataset.tab;
            tabContents.forEach(content => {
                if (content.id === `${target}Tab`) content.classList.remove('hidden');
                else content.classList.add('hidden');
            });
        });
    });

    loadSettings();

    // Initial check for settings: Prompt user if no keys are found
    setTimeout(() => {
        if (!localStorage.getItem('user_ai_gemini_key') && !localStorage.getItem('user_ai_groq_key')) {
            settingsModal.classList.remove('hidden');
            showToast('👋 ยินดีต้อนรับ! กรุณตั่งค่า API Key เพื่อการใช้งานที่เสถียรที่สุดครับ');
        }
    }, 1000);

    // Step 1: Scan Form
    step1Form.addEventListener('submit', async (e) => {
        e.preventDefault();

        currentUrl = document.getElementById('formUrl').value.trim();
        currentEmail = document.getElementById('email').value.trim();

        if (!currentUrl) return;

        scanBtn.disabled = true;
        scanBtn.querySelector('.btn-text').textContent = 'กำลังทำงาน...';
        showLoader('กำลังสแกนคำถามในฟอร์ม กรุณารอสักครู่...');

        try {
            const response = await fetch('/api/parse-form', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    url: currentUrl,
                    user_keys: {
                        gemini: localStorage.getItem('user_ai_gemini_key') || '',
                        groq: localStorage.getItem('user_ai_groq_key') || ''
                    }
                })
            });

            const data = await response.json();

            if (data.success) {
                // Populate Step 2
                formTitle.textContent = data.data.title || "Untitled Form";
                formDescription.textContent = data.data.description || "";
                
                const personalList = document.getElementById('personalQuestionsList');
                const examList = document.getElementById('examQuestionsList');
                const personalSection = document.getElementById('personalSection');
                const examSection = document.getElementById('examSection');
                const noQuestionsMsg = document.getElementById('noQuestionsMsg');
                
                personalList.innerHTML = '';
                examList.innerHTML = '';
                personalSection.style.display = 'none';
                examSection.style.display = 'none';
                noQuestionsMsg.style.display = 'none';
                
                const questions = data.data.questions || [];
                
                if (questions.length === 0) {
                    noQuestionsMsg.style.display = 'block';
                } else {
                    const typeIcons = {
                        text: '<i class="ph ph-text-t" style="margin-right:4px;"></i>',
                        textarea: '<i class="ph ph-article" style="margin-right:4px;"></i>',
                        radio: '<i class="ph ph-radio-button" style="margin-right:4px;"></i>',
                        checkbox: '<i class="ph ph-check-square" style="margin-right:4px;"></i>',
                        dropdown: '<i class="ph ph-caret-down" style="margin-right:4px;"></i>',
                    };
                    const typeLabels = {
                        text: 'ข้อความ',
                        textarea: 'ข้อความยาว',
                        radio: 'เลือกข้อ',
                        checkbox: 'ติ๊กเลือก',
                        dropdown: 'เลือกจากรายการ',
                    };
                    
                    questions.forEach(q => {
                        const qIndex = q.index;
                        const isPersonal = q.category === 'personal';
                        const isTextType = (q.type === 'text' || q.type === 'textarea');
                        const icon = typeIcons[q.type] || '';
                        const typeLabel = typeLabels[q.type] || q.type;
                        
                        // Show options preview for MCQ
                        let optionsPreview = '';
                        if (q.options && q.options.length > 0) {
                            const optsList = q.options.slice(0, 5).map(o => `<span class="option-chip">${o}</span>`).join('');
                            const more = q.options.length > 5 ? `<span class="option-chip">+${q.options.length - 5} อื่นๆ</span>` : '';
                            optionsPreview = `<div class="options-preview">${optsList}${more}</div>`;
                        }
                        
                        if (isPersonal) {
                            // Personal questions: always manual input, no AI toggle
                            let inputField = '';
                            if (isTextType) {
                                inputField = q.type === 'textarea'
                                    ? `<textarea id="ans_${qIndex}" rows="2" placeholder="กรุณาระบุ..." class="personal-input"></textarea>`
                                    : `<input type="text" id="ans_${qIndex}" placeholder="กรุณาระบุ..." class="personal-input">`;
                            } else {
                                // MCQ personal question - show options as radio for user to pick
                                inputField = `<div class="personal-mcq" id="ans_${qIndex}_group">`;
                                (q.options || []).forEach((opt, i) => {
                                    inputField += `<label class="mcq-option-label"><input type="radio" name="personal_${qIndex}" value="${opt}"> ${opt}</label>`;
                                });
                                inputField += '</div>';
                            }
                            
                            const itemHtml = `
                                <div class="question-item personal-question" data-index="${qIndex}" data-category="personal" data-type="${q.type}">
                                    <div class="question-item-header">
                                        <div class="question-title">${icon} ${q.title}</div>
                                        <span class="badge badge-personal"><i class="ph ph-user"></i> ต้องกรอกเอง</span>
                                    </div>
                                    <div class="type-label">${typeLabel}</div>
                                    ${optionsPreview}
                                    <div class="manual-input-container">${inputField}</div>
                                </div>
                            `;
                            personalList.insertAdjacentHTML('beforeend', itemHtml);
                            personalSection.style.display = 'block';
                        } else {
                            // Exam questions: AI/manual toggle
                            let manualInputField = '';
                            if (isTextType) {
                                manualInputField = q.type === 'textarea'
                                    ? `<textarea id="ans_${qIndex}" rows="3" placeholder="ระบุคำตอบของคุณ..."></textarea>`
                                    : `<input type="text" id="ans_${qIndex}" placeholder="ระบุคำตอบของคุณ...">`;
                            } else {
                                // MCQ manual - show options as radio
                                manualInputField = `<div class="personal-mcq" id="ans_${qIndex}_group">`;
                                (q.options || []).forEach((opt, i) => {
                                    manualInputField += `<label class="mcq-option-label"><input type="radio" name="manual_mcq_${qIndex}" value="${opt}"> ${opt}</label>`;
                                });
                                manualInputField += '</div>';
                            }
                            
                            const itemHtml = `
                                <div class="question-item" data-index="${qIndex}" data-category="exam" data-type="${q.type}">
                                    <div class="question-item-header">
                                        <div class="question-title">${icon} ${q.title}</div>
                                        <div class="toggle-group">
                                            <input type="radio" id="ai_${qIndex}" name="mode_${qIndex}" value="ai" checked onchange="toggleManualInput('${qIndex}', false)">
                                            <label for="ai_${qIndex}"><i class="ph ph-sparkle"></i> AI</label>
                                            
                                            <input type="radio" id="manual_${qIndex}" name="mode_${qIndex}" value="manual" onchange="toggleManualInput('${qIndex}', true)">
                                            <label for="manual_${qIndex}"><i class="ph ph-keyboard"></i> พิมพ์เอง</label>
                                        </div>
                                    </div>
                                    <div class="type-label">${typeLabel} ${q.options && q.options.length > 0 ? '(' + q.options.length + ' ตัวเลือก)' : ''}</div>
                                    ${optionsPreview}
                                    <div class="manual-input-container hidden" id="manual_input_${qIndex}">
                                        ${manualInputField}
                                    </div>
                                </div>
                            `;
                            examList.insertAdjacentHTML('beforeend', itemHtml);
                            examSection.style.display = 'block';
                        }
                    });
                }

                // Show Step 2
                step1Form.classList.add('hidden');
                statusContainer.classList.add('hidden');
                step2Container.classList.remove('hidden');
                statusContainer.classList.add('hidden');
                
            } else {
                throw new Error(data.message || 'รหัสลับหรือบอทถูกบล็อกโดย Google Form');
            }
        } catch (error) {
            console.error('Error:', error);
            hideLoader();
            resultBox.classList.remove('hidden');
            resultBox.className = 'result-box error';
            resultIcon.innerHTML = '<i class="ph-fill ph-warning-circle"></i>';
            resultTitle.textContent = 'สแกนฟอร์มไม่สำเร็จ';
            resultMessage.textContent = error.message;
        } finally {
            scanBtn.disabled = false;
            scanBtn.querySelector('.btn-text').textContent = 'สแกนแบบสอบถาม';
        }
    });

    // Toggle logic injected to window for inline onclick handler
    window.toggleManualInput = (index, isManual) => {
        const inputContainer = document.getElementById(`manual_input_${index}`);
        if (inputContainer) {
            if (isManual) {
                inputContainer.classList.remove('hidden');
            } else {
                inputContainer.classList.add('hidden');
            }
        }
    };

    let lastManualAnswers = {};

    // Step 2: Confirmation / Submit to Bot
    startFillBtn.addEventListener('click', async () => {
        // Collect all manual answers (personal + exam manual)
        const manualAnswers = {};
        lastManualAnswers = manualAnswers; // Keep for retry
        
        // Personal questions - always manual
        const personalItems = document.querySelectorAll('.question-item[data-category="personal"]');
        personalItems.forEach(item => {
            const index = item.getAttribute('data-index');
            const type = item.getAttribute('data-type');
            if (type === 'text' || type === 'textarea') {
                const el = document.getElementById(`ans_${index}`);
                if (el && el.value.trim()) {
                    manualAnswers[index] = el.value.trim();
                }
            } else {
                // MCQ personal - get selected radio
                const selected = item.querySelector(`input[name="personal_${index}"]:checked`);
                if (selected) {
                    manualAnswers[index] = selected.value;
                }
            }
        });
        
        // Exam questions - only if manual mode selected
        const examItems = document.querySelectorAll('.question-item[data-category="exam"]');
        examItems.forEach(item => {
            const index = item.getAttribute('data-index');
            const type = item.getAttribute('data-type');
            const isManual = document.getElementById(`manual_${index}`)?.checked;
            if (isManual) {
                if (type === 'text' || type === 'textarea') {
                    const el = document.getElementById(`ans_${index}`);
                    if (el) manualAnswers[index] = el.value.trim();
                } else {
                    const selected = item.querySelector(`input[name="manual_mcq_${index}"]:checked`);
                    if (selected) manualAnswers[index] = selected.value;
                }
            }
        });

        // UI transitions
        step2Container.classList.add('hidden');
        showLoader('ระบบกำลังดำเนินการ เข้าสู่ Google Form และส่งคำตอบอัตโนมัติ (ดูกิจกรรมได้ที่แผงซ้ายมือ)...');
        
        // Show Activity Panel and Start SSE Stream
        activityFeed.innerHTML = '';
        activityPanel.classList.remove('hidden');
        startSSE();

        try {
            const response = await fetch('/api/fill-form', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    url: currentUrl, 
                    email: currentEmail,
                    manual_answers: manualAnswers,
                    user_keys: {
                        gemini: localStorage.getItem('user_ai_gemini_key') || '',
                        groq: localStorage.getItem('user_ai_groq_key') || ''
                    }
                })
            });

            const data = await response.json();
            hideLoader();
            resultBox.classList.remove('hidden');

            if (data.screenshot) {
                const screenEl = document.getElementById('resultScreenshot');
                screenEl.src = data.screenshot + '?t=' + new Date().getTime();
                screenEl.classList.remove('hidden');
            }

            if (data.success) {
                resultBox.className = 'result-box success';
                resultIcon.innerHTML = '<i class="ph-fill ph-check-circle"></i>';
                resultTitle.textContent = 'ส่งฟอร์มสำเร็จ!';
                resultMessage.textContent = data.message || 'ส่งแบบสอบถามเข้า Google Form เรียบร้อยแล้ว';
            } else {
                resultBox.className = 'result-box error';
                resultIcon.innerHTML = '<i class="ph-fill ph-warning-circle"></i>';
                resultTitle.textContent = 'การส่งฟอร์มติดขัด';
                resultMessage.textContent = data.message || 'ไม่สามารถส่งแบบสอบถามได้';

                if (data.required_missing && data.required_missing.length > 0) {
                    renderRepairForm(data.required_missing);
                } else {
                    document.getElementById('repairSection').classList.add('hidden');
                }
            }
        } catch (error) {
            console.error('Error:', error);
            hideLoader();
            resultBox.classList.remove('hidden');
            resultBox.className = 'result-box error';
            resultIcon.innerHTML = '<i class="ph-fill ph-warning-circle"></i>';
            resultTitle.textContent = 'เชื่อมต่อผิดพลาด';
            resultMessage.textContent = 'เซิร์ฟเวอร์ขัดข้อง ไม่สามารถประมวลผลได้';
            appendLog('เซิร์ฟเวอร์ขัดข้อง ไม่สามารถประมวลผลได้', 'error');
        }
    });

    function renderRepairForm(questions) {
        const repairList = document.getElementById('repairQuestionsList');
        const repairSection = document.getElementById('repairSection');
        repairList.innerHTML = '';
        
        questions.forEach(q => {
            // Find if we have options (we might need to scan those first, but for now we'll assume they're visible if they're MCQ)
            // If the backend didn't send options, we default to text
            let inputHtml = '';
            if (q.options && q.options.length > 0) {
                inputHtml = `<div class="personal-mcq" id="repair_ans_${q.index}_group">`;
                q.options.forEach(opt => {
                    inputHtml += `<label class="mcq-option-label"><input type="radio" name="repair_${q.index}" value="${opt}"> ${opt}</label>`;
                });
                inputHtml += '</div>';
            } else {
                inputHtml = `<input type="text" id="repair_ans_${q.index}" class="personal-input" placeholder="ระบุคำตอบที่จำเป็น...">`;
            }
            
            const itemHtml = `
                <div class="question-item repair-item" data-index="${q.index}">
                    <div class="question-title" style="color: var(--text-primary);"><i class="ph ph-warning-circle" style="color: var(--warning);"></i> ${q.title}</div>
                    <div class="manual-input-container">
                        ${inputHtml}
                    </div>
                </div>
            `;
            repairList.insertAdjacentHTML('beforeend', itemHtml);
        });
        
        repairSection.classList.remove('hidden');
    }

    const resubmitBtn = document.getElementById('resubmitBtn');
    resubmitBtn.addEventListener('click', async () => {
        const repairItems = document.querySelectorAll('.repair-item');
        repairItems.forEach(item => {
            const index = item.getAttribute('data-index');
            const radio = item.querySelector(`input[name="repair_${index}"]:checked`);
            const text = document.getElementById(`repair_ans_${index}`);
            
            if (radio) {
                lastManualAnswers[index] = radio.value;
            } else if (text && text.value.trim()) {
                lastManualAnswers[index] = text.value.trim();
            }
        });

        // Hide result and show loader again
        document.getElementById('resultBox').classList.add('hidden');
        document.getElementById('repairSection').classList.add('hidden');
        showLoader('กำลังส่งแบบสอบถามใหม่อีกครั้ง...');
        
        try {
            const response = await fetch('/api/fill-form', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    url: currentUrl, 
                    email: currentEmail,
                    manual_answers: lastManualAnswers,
                    user_keys: {
                        gemini: localStorage.getItem('user_ai_gemini_key') || '',
                        groq: localStorage.getItem('user_ai_groq_key') || ''
                    }
                })
            });

            const data = await response.json();
            hideLoader();
            const resultBox = document.getElementById('resultBox');
            const resultIcon = document.getElementById('resultIcon');
            const resultTitle = document.getElementById('resultTitle');
            const resultMessage = document.getElementById('resultMessage');
            
            resultBox.classList.remove('hidden');
            if (data.success) {
                resultBox.className = 'result-box success';
                resultIcon.innerHTML = '<i class="ph-fill ph-check-circle"></i>';
                resultTitle.textContent = 'ส่งฟอร์มสำเร็จ!';
                resultMessage.textContent = data.message || 'ส่งแบบสอบถามเรียบร้อยแล้ว';
                document.getElementById('repairSection').classList.add('hidden');
            } else {
                resultBox.className = 'result-box error';
                resultIcon.innerHTML = '<i class="ph-fill ph-warning-circle"></i>';
                resultTitle.textContent = 'ยังติดขัดบางประการ';
                resultMessage.textContent = data.message || 'กรุณาตรวจสอบข้อที่เหลือ';
                if (data.required_missing && data.required_missing.length > 0) {
                    renderRepairForm(data.required_missing);
                }
            }
        } catch (e) {
            hideLoader();
            alert('เกิดข้อผิดพลาดในการส่งซ้ำ');
        }
    });

    // Reset Flow
    backBtn.addEventListener('click', () => {
        step2Container.classList.add('hidden');
        step1Form.classList.remove('hidden');
    });

    resetBtn.addEventListener('click', () => {
        activityPanel.classList.add('hidden');
        statusContainer.classList.add('hidden');
        resultBox.classList.add('hidden');
        document.getElementById('resultScreenshot').classList.add('hidden');
        document.getElementById('repairSection').classList.add('hidden');
        step1Form.classList.remove('hidden');
        document.getElementById('formUrl').value = '';
    });
});
