/**
 * 3D Model Viewer and PDF Page Capturer for ReportPDFmaker Web
 * Uses Three.js & GLTFLoader to interactively preview 3D models (GLTF/GLB)
 * and capture clean snapshots to document pages.
 */

import { PageItem } from './state.js';
import { loadImage } from './converters.js';

export class ThreeViewerModal {
  constructor(modalId, canvasContainerId) {
    this.modal = document.getElementById(modalId);
    this.container = document.getElementById(canvasContainerId);
    this.renderer = null;
    this.scene = null;
    this.camera = null;
    this.controls = null;
    this.currentModel = null;
    this.animId = null;
    this.currentFileName = '3d-model';

    this.onCaptureCallback = null;
    // Initialize WebGL only when a 3D file is opened.
  }

  init() {
    if (!window.THREE) return;

    const w = this.container.clientWidth || 640;
    const h = this.container.clientHeight || 480;

    this.scene = new window.THREE.Scene();
    this.scene.background = new window.THREE.Color(0xf8fafc);

    this.camera = new window.THREE.PerspectiveCamera(45, w / h, 0.1, 1000);
    this.camera.position.set(0, 2, 5);

    this.renderer = new window.THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
    this.renderer.setSize(w, h);
    this.renderer.setPixelRatio(window.devicePixelRatio || 1);
    this.renderer.outputEncoding = window.THREE.sRGBEncoding;
    this.container.appendChild(this.renderer.domElement);

    if (window.THREE.OrbitControls) {
      this.controls = new window.THREE.OrbitControls(this.camera, this.renderer.domElement);
      this.controls.enableDamping = true;
      this.controls.dampingFactor = 0.05;
    }

    // Lights
    const hemiLight = new window.THREE.HemisphereLight(0xffffff, 0x444444, 1.2);
    hemiLight.position.set(0, 20, 0);
    this.scene.add(hemiLight);

    const dirLight = new window.THREE.DirectionalLight(0xffffff, 1.0);
    dirLight.position.set(5, 10, 7);
    this.scene.add(dirLight);

    const backLight = new window.THREE.DirectionalLight(0xffffff, 0.5);
    backLight.position.set(-5, -5, -5);
    this.scene.add(backLight);

    // Grid helper
    const grid = new window.THREE.GridHelper(10, 10, 0x94a3b8, 0xe2e8f0);
    this.scene.add(grid);

    this.animate = this.animate.bind(this);
    this.animate();
  }

  animate() {
    this.animId = requestAnimationFrame(this.animate);
    if (this.controls) this.controls.update();
    if (this.renderer && this.scene && this.camera) {
      this.renderer.render(this.scene, this.camera);
    }
  }

  async loadModel(file, onCapture) {
    if (!window.THREE?.GLTFLoader) throw new Error('3D preview libraries are unavailable.');
    if (!this.renderer) {
      try { this.init(); } catch { throw new Error('3D preview requires WebGL. Other PDF tools remain available.'); }
    }
    this.onCaptureCallback = onCapture;
    this.currentFileName = file.name;
    this.modal.classList.remove('hidden');

    // Resize renderer to container
    setTimeout(() => {
      const w = this.container.clientWidth;
      const h = this.container.clientHeight;
      this.renderer.setSize(w, h);
      this.camera.aspect = w / h;
      this.camera.updateProjectionMatrix();
    }, 50);

    const arrayBuffer = await file.arrayBuffer();
    const loader = new window.THREE.GLTFLoader();

    loader.parse(arrayBuffer, '', (gltf) => {
      if (this.currentModel) {
        this.scene.remove(this.currentModel);
      }
      this.currentModel = gltf.scene;

      // Center and scale model
      const box = new window.THREE.Box3().setFromObject(this.currentModel);
      const size = box.getSize(new window.THREE.Vector3());
      const center = box.getCenter(new window.THREE.Vector3());

      this.currentModel.position.x -= center.x;
      this.currentModel.position.y -= center.y;
      this.currentModel.position.z -= center.z;

      const maxDim = Math.max(size.x, size.y, size.z);
      const scale = 3.0 / (maxDim || 1);
      this.currentModel.scale.set(scale, scale, scale);

      this.scene.add(this.currentModel);

      // Reset camera
      this.camera.position.set(0, 1.5, 4);
      if (this.controls) {
        this.controls.target.set(0, 0, 0);
        this.controls.update();
      }
    }, (err) => {
      console.error('Failed to parse 3D file:', err);
      alert('Could not parse 3D file. Please ensure it is a valid .gltf or .glb format.');
      this.close();
    });
  }

  async captureSnapshot() {
    if (!this.renderer) return;

    // Render snapshot
    this.renderer.render(this.scene, this.camera);
    const dataUrl = this.renderer.domElement.toDataURL('image/png');
    const img = await loadImage(dataUrl);

    // Create thumbnail
    const thumbCanvas = document.createElement('canvas');
    thumbCanvas.width = 180;
    thumbCanvas.height = 180;
    const tctx = thumbCanvas.getContext('2d');
    tctx.drawImage(img, 0, 0, 180, 180);
    const thumbUrl = thumbCanvas.toDataURL('image/jpeg', 0.85);

    const pageItem = new PageItem({
      name: `${this.currentFileName} (3D View)`,
      sourceType: '3d',
      sourceImage: img,
      thumbnailUrl: thumbUrl,
      pageLandscape: false
    });

    if (this.onCaptureCallback) {
      this.onCaptureCallback(pageItem);
    }

    this.close();
  }

  close() {
    this.modal.classList.add('hidden');
    if (this.currentModel) {
      this.scene.remove(this.currentModel);
      this.currentModel = null;
    }
  }
}
