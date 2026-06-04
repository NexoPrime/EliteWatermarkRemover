import React, { useState, useRef, useEffect } from 'react';

// Declare cv globally for TypeScript
declare const cv: any;

function App() {
  const [cvReady, setCvReady] = useState(false);
  const [imageLoaded, setImageLoaded] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const overlayRef = useRef<HTMLCanvasElement>(null);
  
  const [isDrawing, setIsDrawing] = useState(false);
  const [brushSize, setBrushSize] = useState(15);
  
  // Base image and mask Mats
  const imgMatRef = useRef<any>(null);
  const maskMatRef = useRef<any>(null);

  useEffect(() => {
    // Check if OpenCV is loaded
    const checkCv = setInterval(() => {
      if (typeof cv !== 'undefined' && cv.Mat) {
        setCvReady(true);
        clearInterval(checkCv);
      }
    }, 500);
    return () => clearInterval(checkCv);
  }, []);

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const file = e.target.files[0];
    const img = new Image();
    img.src = URL.createObjectURL(file);
    img.onload = () => {
      const canvas = canvasRef.current!;
      const overlay = overlayRef.current!;
      const ctx = canvas.getContext('2d')!;
      
      // Calculate scaled dimensions to fit screen while maintaining aspect ratio
      const maxWidth = window.innerWidth - 400; // Leave room for sidebar
      const maxHeight = window.innerHeight - 100;
      
      let width = img.width;
      let height = img.height;
      
      if (width > maxWidth || height > maxHeight) {
        const ratio = Math.min(maxWidth / width, maxHeight / height);
        width = width * ratio;
        height = height * ratio;
      }
      
      canvas.width = width;
      canvas.height = height;
      overlay.width = width;
      overlay.height = height;
      
      ctx.drawImage(img, 0, 0, width, height);
      
      if (imgMatRef.current) imgMatRef.current.delete();
      if (maskMatRef.current) maskMatRef.current.delete();
      
      imgMatRef.current = cv.imread(canvas);
      maskMatRef.current = new cv.Mat.zeros(imgMatRef.current.rows, imgMatRef.current.cols, cv.CV_8UC1);
      
      setImageLoaded(true);
    };
  };

  const startDrawing = (e: React.MouseEvent<HTMLCanvasElement>) => {
    setIsDrawing(true);
    draw(e);
  };

  const stopDrawing = () => {
    setIsDrawing(false);
    const overlay = overlayRef.current!;
    const ctx = overlay.getContext('2d')!;
    ctx.beginPath();
  };

  const draw = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isDrawing) return;
    const overlay = overlayRef.current!;
    const ctx = overlay.getContext('2d')!;
    
    const rect = overlay.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    ctx.lineWidth = brushSize;
    ctx.lineCap = 'round';
    ctx.strokeStyle = 'rgba(0, 229, 255, 0.4)'; // Cyber-cyan brush visual
    
    ctx.lineTo(x, y);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(x, y);
    
    // Draw on the actual OpenCV mask (must be solid white 255)
    if (maskMatRef.current) {
      cv.circle(maskMatRef.current, new cv.Point(x, y), brushSize/2, new cv.Scalar(255, 255, 255, 255), -1);
    }
  };

  const handleInpaint = () => {
    if (!imageLoaded || !cvReady || !imgMatRef.current || !maskMatRef.current) return;
    
    setIsProcessing(true);
    
    // Use setTimeout to allow UI to show loader before heavy synchronous processing
    setTimeout(() => {
      try {
        const dst = new cv.Mat();
        // Convert image to RGB if needed (imread creates RGBA on canvas)
        const rgbMat = new cv.Mat();
        cv.cvtColor(imgMatRef.current, rgbMat, cv.COLOR_RGBA2RGB, 0);
        
        // cv.INPAINT_TELEA = 1, cv.INPAINT_NS = 0
        cv.inpaint(rgbMat, maskMatRef.current, dst, 3, cv.INPAINT_TELEA);
        
        cv.imshow(canvasRef.current!, dst);
        
        // Clear overlay
        const overlay = overlayRef.current!;
        const ctx = overlay.getContext('2d')!;
        ctx.clearRect(0, 0, overlay.width, overlay.height);
        
        // Update references
        imgMatRef.current.delete();
        imgMatRef.current = dst.clone(); // Note: dst is RGB
        
        // Reset mask
        maskMatRef.current.setTo(new cv.Scalar(0, 0, 0, 0));
        
        dst.delete();
        rgbMat.delete();
      } catch (err) {
        console.error("Inpainting failed", err);
        alert("Inpainting error: " + err);
      } finally {
        setIsProcessing(false);
      }
    }, 50);
  };

  const handleDownload = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const link = document.createElement('a');
    link.download = 'elite_result.png';
    link.href = canvas.toDataURL('image/png');
    link.click();
  };

  return (
    <div className="app-container">
      <div className="sidebar glass-panel">
        <h1 className="logo-text">Elite Web Pro</h1>
        
        {!cvReady && (
          <div style={{color: 'var(--accent-cyan)'}}>Initializing AI Engine...</div>
        )}
        
        <div className="control-group" style={{marginTop: '20px'}}>
          <label>1. Upload Image</label>
          <input 
            type="file" 
            accept="image/*" 
            onChange={handleImageUpload}
            style={{display: 'none'}}
            id="file-upload"
          />
          <label htmlFor="file-upload" className="elite-btn secondary" style={{textAlign: 'center', display: 'block'}}>
            Choose File
          </label>
        </div>

        <div className="control-group">
          <label>2. Brush Size ({brushSize}px)</label>
          <input 
            type="range" 
            min="5" 
            max="100" 
            value={brushSize}
            onChange={(e) => setBrushSize(parseInt(e.target.value))}
            style={{width: '100%'}}
          />
        </div>

        <button 
          className="elite-btn" 
          onClick={handleInpaint}
          disabled={!imageLoaded || !cvReady || isProcessing}
          style={{marginTop: '10px'}}
        >
          {isProcessing ? 'Processing...' : 'Run Elite AI'}
        </button>

        <button 
          className="elite-btn secondary" 
          onClick={handleDownload}
          disabled={!imageLoaded || isProcessing}
        >
          Download Result
        </button>
      </div>

      <div className="main-workspace">
        {isProcessing && (
          <div className="cv-loader">
            <div className="spinner"></div>
            <h3>Neural Network Processing...</h3>
          </div>
        )}
        
        <div className="canvas-container">
          <canvas ref={canvasRef} style={{position: 'absolute', top: 0, left: 0}} />
          <canvas 
            ref={overlayRef} 
            onMouseDown={startDrawing}
            onMouseUp={stopDrawing}
            onMouseOut={stopDrawing}
            onMouseMove={draw}
            style={{cursor: 'crosshair', position: 'relative'}}
          />
        </div>
      </div>
    </div>
  );
}

export default App;
