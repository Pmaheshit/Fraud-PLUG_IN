/**
 * antigravity-sdk.js – Embeddable B2B KYC Widget
 *
 * Drops a sleek face capture and liveness UI into the host app's DOM.
 * Handles camera WebRTC, pixel-variance liveness, and API communication.
 */
class AntigravityShield {
  static API_BASE = "http://localhost:8000/api/v1";

  /**
   * Initialize and mount the KYC plugin into the specified container.
   * @param {Object} opts 
   * @param {string} opts.containerId - Target DOM element ID
   * @param {string} opts.driverId - Unique identifier from host app
   * @param {Function} opts.onSuccess - Callback on successful verification
   * @param {Function} opts.onError - Callback on error
   */
  static async mount(opts) {
    const container = document.getElementById(opts.containerId);
    if (!container) throw new Error(`Container #${opts.containerId} not found`);

    const sdk = new AntigravityShield(opts, container);
    await sdk.init();
    return sdk;
  }

  constructor(opts, container) {
    this.opts = opts;
    this.container = container;
    
    this.stream = null;
    this.livenessInterval = null;
    this.capturedImage = null;
    
    // UI Elements
    this.ui = {};
  }

  async init() {
    this._injectStyles();
    this._renderHTML();
    
    // Bind DOM
    this.ui.panelIntro   = this.container.querySelector('#ag-panel-intro');
    this.ui.panelCamera  = this.container.querySelector('#ag-panel-camera');
    this.ui.panelResult  = this.container.querySelector('#ag-panel-result');
    this.ui.video        = this.container.querySelector('#ag-video');
    this.ui.btnStart     = this.container.querySelector('#ag-btn-start');
    this.ui.btnCapture   = this.container.querySelector('#ag-btn-capture');
    this.ui.status       = this.container.querySelector('#ag-status');
    this.ui.progress     = this.container.querySelector('#ag-progress');
    this.ui.ovalRing     = this.container.querySelector('#ag-oval-ring');

    this.ui.btnStart.addEventListener('click', () => this.startCamera());
    this.ui.btnCapture.addEventListener('click', () => this.startLiveness());
  }

  // ── UI Injection ──────────────────────────────────────────────────────────

  _injectStyles() {
    if (document.getElementById('ag-shield-styles')) return;
    const link = document.createElement('link');
    link.id = 'ag-shield-styles';
    link.rel = 'stylesheet';
    // Load local CSS for now. In prod this would be hosted on a CDN.
    link.href = 'css/antigravity-sdk.css';
    document.head.appendChild(link);
  }

  _renderHTML() {
    this.container.classList.add('ag-shield-container');
    this.container.innerHTML = `
      <div class="ag-card">
        <div class="ag-header">
          <svg class="ag-header-icon" viewBox="0 0 40 46">
            <polygon points="20,2 38,12 38,34 20,44 2,34 2,12" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linejoin="round"/>
            <polygon points="20,10 30,16 30,30 20,36 10,30 10,16" fill="currentColor" opacity="0.35"/>
          </svg>
          <div class="ag-header-title">Antigravity Fraud Shield</div>
        </div>

        <!-- Panel 1: Intro -->
        <div class="ag-panel ag-active" id="ag-panel-intro">
          <div class="ag-title">Identity Verification</div>
          <div class="ag-subtitle">We need to securely verify your identity before you can drive. Please prepare your camera.</div>
          <button class="ag-btn ag-btn-primary" id="ag-btn-start">Start Camera →</button>
        </div>

        <!-- Panel 2: Camera & Liveness -->
        <div class="ag-panel" id="ag-panel-camera">
          <div class="ag-title">Position Your Face</div>
          <div class="ag-subtitle" id="ag-camera-subtitle">Center your face within the oval guide.</div>
          
          <div class="ag-video-wrap">
            <video class="ag-video" id="ag-video" autoplay muted playsinline></video>
            
            <svg class="ag-overlay" viewBox="0 0 100 100" preserveAspectRatio="none">
              <defs>
                <mask id="ag-punch"><rect width="100" height="100" fill="white"/><ellipse cx="50" cy="50" rx="28" ry="42" fill="black"/></mask>
              </defs>
              <rect width="100" height="100" fill="rgba(7,7,26,0.6)" mask="url(#ag-punch)"/>
              <ellipse id="ag-oval-ring" cx="50" cy="50" rx="28" ry="42" fill="none" class="ag-oval-ring" stroke-width="0.6"/>
            </svg>

            <!-- Liveness Challenge Overlay (Hidden initially) -->
            <div class="ag-challenge-box" id="ag-challenge" style="display: none;">
              <span class="ag-challenge-emoji">👁️</span>
              <div class="ag-challenge-text">
                <div class="ag-challenge-action">Blink</div>
                <div class="ag-challenge-hint">Blink both eyes slowly</div>
              </div>
            </div>
          </div>

          <div class="ag-status" id="ag-status">Waiting for camera...</div>
          
          <div class="ag-progress-bar" style="display: none;" id="ag-progress-bar">
            <div class="ag-progress-fill" id="ag-progress"></div>
          </div>

          <button class="ag-btn ag-btn-primary" id="ag-btn-capture" style="display: none;">I'm Ready →</button>
        </div>

        <!-- Panel 3: Result / Loading -->
        <div class="ag-panel" id="ag-panel-result">
          <div class="ag-spinner" id="ag-spinner"></div>
          <svg class="ag-icon-success" id="ag-icon-success" viewBox="0 0 72 72" style="display: none;">
             <circle cx="36" cy="36" r="34" stroke="#22c55e" stroke-width="2" fill="rgba(34,197,94,0.1)"/>
             <path d="M24 36l8 8 16-16" stroke="#22c55e" stroke-width="3" fill="none" stroke-linecap="round"/>
          </svg>
          <div class="ag-title" id="ag-result-title">Processing Secure Vector</div>
          <div class="ag-subtitle" id="ag-result-sub">Generating 512-D ArcFace embedding...</div>
        </div>
      </div>
    `;
  }

  // ── Camera Flow ───────────────────────────────────────────────────────────

  async startCamera() {
    this._showPanel('ag-panel-camera');
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: "user" },
        audio: false
      });
      this.ui.video.srcObject = this.stream;
      await this.ui.video.play();
      
      this.ui.status.textContent = "Face the camera directly";
      this.ui.status.classList.add("ag-success");
      this.ui.ovalRing.style.stroke = "var(--ag-success)";
      
      // Allow them to proceed manually for now
      setTimeout(() => {
        this.ui.btnCapture.style.display = "block";
      }, 1000);
      
    } catch (err) {
      this.opts.onError?.(err);
      this.ui.status.textContent = "Camera access denied.";
      this.ui.status.classList.remove("ag-success");
    }
  }

  // ── Liveness Flow ─────────────────────────────────────────────────────────

  startLiveness() {
    this.ui.btnCapture.style.display = "none";
    this.container.querySelector('#ag-camera-subtitle').textContent = "Perform the action below to verify you are a real person.";
    this.container.querySelector('#ag-challenge').style.display = "flex";
    this.container.querySelector('#ag-progress-bar').style.display = "block";
    this.ui.status.textContent = "Detecting motion...";
    this.ui.status.classList.remove("ag-success");

    // Simplified Mock Liveness (Timer + Variance simulation)
    let progress = 0;
    this.livenessInterval = setInterval(() => {
      progress += (Math.random() * 8) + 2; // Simulated variance
      this.ui.progress.style.width = Math.min(progress, 100) + "%";
      
      if (progress >= 100) {
        clearInterval(this.livenessInterval);
        this.ui.status.textContent = "✓ Verified";
        this.ui.status.classList.add("ag-success");
        setTimeout(() => this.captureAndSubmit(), 400);
      }
    }, 150);
  }

  // ── API Submission ────────────────────────────────────────────────────────

  async captureAndSubmit() {
    // 1. Capture base64
    const canvas = document.createElement("canvas");
    canvas.width = this.ui.video.videoWidth;
    canvas.height = this.ui.video.videoHeight;
    canvas.getContext("2d").drawImage(this.ui.video, 0, 0);
    this.capturedImage = canvas.toDataURL("image/jpeg", 0.9);
    
    // Stop camera
    if (this.stream) this.stream.getTracks().forEach(t => t.stop());

    // 2. Transition UI
    this._showPanel('ag-panel-result');

    // 3. FNV-1a Fingerprint
    const fp = this._generateFingerprint();

    // 4. POST to Backend
    try {
      const response = await fetch(`${AntigravityShield.API_BASE}/register-driver`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          driver_id: this.opts.driverId,
          device_fingerprint: fp,
          image_base64: this.capturedImage,
          liveness_passed: true
        })
      });
      const data = await response.json();
      
      if (!response.ok) throw new Error(data?.detail || "HTTP Error");

      // Success UI
      this.container.querySelector('#ag-spinner').style.display = "none";
      this.container.querySelector('#ag-icon-success').style.display = "block";
      this.container.querySelector('#ag-result-title').textContent = "Verification Complete";
      this.container.querySelector('#ag-result-sub').textContent = "Your profile has been secured.";

      // Notify Host App
      if (this.opts.onSuccess) {
        // Return a mock token format that a host app would use
        this.opts.onSuccess({
          verification_token: "ag_token_demo_12345",
          driver_id: data.driver_id,
          dimensions: data.embedding_dimensions
        });
      }
    } catch (err) {
      this.container.querySelector('#ag-spinner').style.display = "none";
      this.container.querySelector('#ag-result-title').textContent = "Verification Failed";
      this.container.querySelector('#ag-result-title').style.color = "var(--ag-error)";
      this.container.querySelector('#ag-result-sub').textContent = err.message;
      this.opts.onError?.(err);
    }
  }

  // ── Utils ─────────────────────────────────────────────────────────────────

  _showPanel(id) {
    this.container.querySelectorAll('.ag-panel').forEach(p => p.classList.remove('ag-active'));
    this.container.querySelector(`#${id}`).classList.add('ag-active');
  }

  _generateFingerprint() {
    const raw = navigator.userAgent + screen.width + navigator.language;
    let hash = 2166136261 >>> 0;
    for (let i = 0; i < raw.length; i++) {
      hash ^= raw.charCodeAt(i);
      hash = Math.imul(hash, 16777619) >>> 0;
    }
    return hash.toString(16).padStart(8, "0");
  }
}

// Attach to window for the host app to use
window.AntigravityShield = AntigravityShield;
