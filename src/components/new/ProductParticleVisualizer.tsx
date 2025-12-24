/**
 * ProductParticleVisualizer - Three.js particle system for product logos
 * 
 * Creates a 3D particle effect where particles form the shape of a product logo
 * using MeshSurfaceSampler technique (like IGLOO website).
 * 
 * Supports:
 * - SVG logo loading and extrusion to 3D
 * - Surface sampling for accurate logo shape
 * - Animated "flowing" particles effect
 * - Mouse parallax interaction
 * - Mobile optimization (fewer particles)
 */

import React, { useRef, useEffect, useCallback, useState } from 'react';
import * as THREE from 'three';
import { SVGLoader } from 'three/examples/jsm/loaders/SVGLoader.js';
import { MeshSurfaceSampler } from 'three/examples/jsm/math/MeshSurfaceSampler.js';
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';

interface ProductParticleVisualizerProps {
  logoUrl?: string; // SVG logo URL
  fallbackShape?: 'torus' | 'box' | 'sphere' | 'text'; // Fallback if no SVG
  text?: string; // Text to display if fallbackShape is 'text'
  color?: string; // Particle color (hex)
  backgroundColor?: string; // Background color
  particleCount?: number; // Number of particles (auto-adjusted for mobile)
  className?: string;
  onLoad?: () => void;
  onError?: (error: Error) => void;
}

// Helper to create soft particle texture programmatically
const createParticleTexture = () => {
  const canvas = document.createElement('canvas');
  canvas.width = 32;
  canvas.height = 32;
  const ctx = canvas.getContext('2d');
  if (!ctx) return new THREE.Texture();

  const gradient = ctx.createRadialGradient(16, 16, 0, 16, 16, 16);
  gradient.addColorStop(0, 'rgba(255, 255, 255, 1)'); // Center
  gradient.addColorStop(0.4, 'rgba(255, 255, 255, 0.5)'); // Mid
  gradient.addColorStop(1, 'rgba(0, 0, 0, 0)'); // Edge

  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, 32, 32);

  const texture = new THREE.CanvasTexture(canvas);
  return texture;
};

const ProductParticleVisualizer: React.FC<ProductParticleVisualizerProps> = ({
  logoUrl,
  fallbackShape = 'torus',
  text,
  color = '#00FFFF', // Pandora Cyan
  backgroundColor = '#050505', // Deep dark
  particleCount: propParticleCount,
  className = '',
  onLoad,
  onError,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const particleMaterialRef = useRef<THREE.ShaderMaterial | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const clockRef = useRef<THREE.Clock | null>(null);
  const mouseRef = useRef({ x: 0, y: 0 });
  const [isLoaded, setIsLoaded] = useState(false);

  // Calculate particle count (Balanced for visual quality vs performance)
  const getParticleCount = useCallback(() => {
    if (propParticleCount) return propParticleCount;
    const isMobile = window.innerWidth < 768;
    return isMobile ? 40000 : 80000; // Balanced for PointsMaterial
  }, [propParticleCount]);

  // Create fallback geometry
  const createFallbackGeometry = useCallback((shape: string): THREE.BufferGeometry => {
    switch (shape) {
      case 'box':
        return new THREE.BoxGeometry(4, 4, 4, 8, 8, 8);
      case 'sphere':
        return new THREE.SphereGeometry(3, 32, 32);
      case 'torus':
      default:
        return new THREE.TorusKnotGeometry(2, 0.6, 100, 16);
    }
  }, []);

  // Create particles from geometry with normals for lighting
  const createParticlesFromGeometry = useCallback((
    geometry: THREE.BufferGeometry,
    scene: THREE.Scene,
    particleColor: string
  ) => {
    // Create mesh for sampling (with normals)
    geometry.computeVertexNormals();
    const material = new THREE.MeshBasicMaterial();
    const mesh = new THREE.Mesh(geometry, material);
    
    console.log('[ProductParticleVisualizer] Mesh geometry vertices:', geometry.attributes.position?.count);
    
    // Sample surface with normals
    const sampler = new MeshSurfaceSampler(mesh).build();
    console.log('[ProductParticleVisualizer] Sampler built');
    const count = getParticleCount();
    
    const particlesGeometry = new THREE.BufferGeometry();
    const positions = new Float32Array(count * 3);
    const normals = new Float32Array(count * 3);
    const randomness = new Float32Array(count * 3);
    
    const tempPosition = new THREE.Vector3();
    const tempNormal = new THREE.Vector3();
    let validSamples = 0;
    
    for (let i = 0; i < count; i++) {
      sampler.sample(tempPosition, tempNormal);
      
      // Check for valid position (not NaN)
      if (isNaN(tempPosition.x) || isNaN(tempPosition.y) || isNaN(tempPosition.z)) {
        // Fallback: random position in a sphere
        const theta = Math.random() * Math.PI * 2;
        const phi = Math.acos(2 * Math.random() - 1);
        const r = 3 * Math.cbrt(Math.random());
        tempPosition.x = r * Math.sin(phi) * Math.cos(theta);
        tempPosition.y = r * Math.sin(phi) * Math.sin(theta);
        tempPosition.z = r * Math.cos(phi);
        tempNormal.set(0, 1, 0); // Default normal up
      } else {
        validSamples++;
      }
      
      positions[i * 3] = tempPosition.x;
      positions[i * 3 + 1] = tempPosition.y;
      positions[i * 3 + 2] = tempPosition.z;
      
      normals[i * 3] = tempNormal.x;
      normals[i * 3 + 1] = tempNormal.y;
      normals[i * 3 + 2] = tempNormal.z;
      
      randomness[i * 3] = Math.random();
      randomness[i * 3 + 1] = Math.random();
      randomness[i * 3 + 2] = Math.random();
    }
    
    console.log('[ProductParticleVisualizer] Valid samples:', validSamples, 'of', count);
    
    particlesGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    
    // Create soft particle texture
    const texture = createParticleTexture();
    
    // Create standard PointsMaterial with texture for "expensive" look
    const particleMaterial = new THREE.PointsMaterial({
      color: new THREE.Color(particleColor),
      size: 0.15,          // Adjust based on scale
      map: texture,
      transparent: true,
      opacity: 0.8,
      alphaTest: 0.001,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      sizeAttenuation: true
    });
    
    particleMaterialRef.current = particleMaterial as any;
    
    const particles = new THREE.Points(particlesGeometry, particleMaterial);
    scene.add(particles);
    
    console.log('[ProductParticleVisualizer] Particles created:', count, 'added to scene');
    console.log('[ProductParticleVisualizer] Scene children:', scene.children.length);
    
    // Cleanup mesh
    material.dispose();
    
    return particles;
  }, [getParticleCount]);

  // Load SVG and create geometry
  const loadSVGLogo = useCallback((url: string): Promise<THREE.BufferGeometry> => {
    return new Promise((resolve, reject) => {
      const loader = new SVGLoader();
      
      console.log('[ProductParticleVisualizer] Loading SVG:', url);
      
      loader.load(
        url,
        (data) => {
          console.log('[ProductParticleVisualizer] SVG loaded, paths:', data.paths.length);
          const paths = data.paths;
          const shapes: THREE.Shape[] = [];
          
          paths.forEach((path, index) => {
            const pathShapes = SVGLoader.createShapes(path);
            console.log(`[ProductParticleVisualizer] Path ${index}: ${pathShapes.length} shapes`);
            shapes.push(...pathShapes);
          });
          
          console.log('[ProductParticleVisualizer] Total shapes:', shapes.length);
          
          if (shapes.length === 0) {
            reject(new Error('No shapes found in SVG'));
            return;
          }
          
          // Extrude to 3D
          const extrudeSettings = {
            depth: 0.5,
            bevelEnabled: true,
            bevelThickness: 0.1,
            bevelSize: 0.1,
            bevelSegments: 2,
          };
          
          const geometry = new THREE.ExtrudeGeometry(shapes, extrudeSettings);
          
          console.log('[ProductParticleVisualizer] Extruded geometry vertices:', geometry.attributes.position?.count);
          
          // Center the geometry
          geometry.computeBoundingBox();
          const box = geometry.boundingBox!;
          const center = new THREE.Vector3();
          box.getCenter(center);
          geometry.translate(-center.x, -center.y, -center.z);
          
          // Scale to fit (bigger for more presence)
          const size = new THREE.Vector3();
          box.getSize(size);
          const maxDim = Math.max(size.x, size.y, size.z);
          const scale = 6 / maxDim; // Balanced scale
          console.log('[ProductParticleVisualizer] Geometry size:', size.x, size.y, size.z, 'scale:', scale);
          geometry.scale(scale, -scale, scale); // Flip Y for SVG
          
          console.log('[ProductParticleVisualizer] Final geometry ready');
          resolve(geometry);
        },
        (progress) => {
          console.log('[ProductParticleVisualizer] Loading progress:', progress.loaded);
        },
        (error) => {
          console.error('[ProductParticleVisualizer] SVG load error:', error);
          reject(error);
        }
      );
    });
  }, []);

  // Initialize Three.js scene
  useEffect(() => {
    if (!containerRef.current) return;

    const container = containerRef.current;
    const width = container.clientWidth || 400;
    const height = container.clientHeight || 400;
    
    console.log('[ProductParticleVisualizer] Container size:', width, 'x', height);

    // Scene
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(backgroundColor);
    sceneRef.current = scene;

    // Camera
    const camera = new THREE.PerspectiveCamera(75, width / height, 0.1, 1000);
    camera.position.z = 10;
    cameraRef.current = camera;

    // Renderer
    const renderer = new THREE.WebGLRenderer({ 
      antialias: true,
      alpha: true,
    });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.domElement.style.position = 'absolute';
    renderer.domElement.style.top = '0';
    renderer.domElement.style.left = '0';
    renderer.domElement.style.width = '100%';
    renderer.domElement.style.height = '100%';
    container.appendChild(renderer.domElement);
    rendererRef.current = renderer;
    
    console.log('[ProductParticleVisualizer] Renderer created, canvas:', renderer.domElement.width, 'x', renderer.domElement.height);

    // Post-processing (Bloom)
    const renderScene = new RenderPass(scene, camera);

    const bloomPass = new UnrealBloomPass(new THREE.Vector2(width, height), 1.5, 0.4, 0.85);
    bloomPass.threshold = 0.1; // Glow threshold
    bloomPass.strength = 1.5;  // Glow strength (high for neon look)
    bloomPass.radius = 0.5;    // Glow radius

    const composer = new EffectComposer(renderer);
    composer.addPass(renderScene);
    composer.addPass(bloomPass);

    // Clock
    const clock = new THREE.Clock();
    clockRef.current = clock;

    // Load geometry and create particles
    const initParticles = async () => {
      try {
        let geometry: THREE.BufferGeometry;
        
        if (logoUrl) {
          geometry = await loadSVGLogo(logoUrl);
        } else {
          geometry = createFallbackGeometry(fallbackShape);
        }
        
        createParticlesFromGeometry(geometry, scene, color);
        geometry.dispose();
        
        setIsLoaded(true);
        onLoad?.();
        
        // Start animation AFTER particles are ready
        console.log('[ProductParticleVisualizer] Starting animation loop after particles ready');
        animate();
      } catch (error) {
        console.warn('Failed to load logo, using fallback:', error);
        const geometry = createFallbackGeometry(fallbackShape);
        createParticlesFromGeometry(geometry, scene, color);
        geometry.dispose();
        
        setIsLoaded(true);
        onError?.(error as Error);
        
        // Start animation even on fallback
        animate();
      }
    };

    // Animation loop
    let frameCount = 0;
    const animate = () => {
      if (!clockRef.current || !particleMaterialRef.current || !sceneRef.current || !cameraRef.current || !rendererRef.current) {
        console.warn('[ProductParticleVisualizer] Animation loop missing refs');
        return;
      }
      
      frameCount++;
      if (frameCount === 1) {
        console.log('[ProductParticleVisualizer] First frame rendered');
      }
      
      const elapsedTime = clockRef.current.getElapsedTime();
      
      // Update custom uniforms if material is shader material
      if (particleMaterialRef.current instanceof THREE.ShaderMaterial) {
          particleMaterialRef.current.uniforms.uTime.value = elapsedTime;
          particleMaterialRef.current.uniforms.uMouseX.value = mouseRef.current.x;
          particleMaterialRef.current.uniforms.uMouseY.value = mouseRef.current.y;
      }
      
      // Elegant rotation
      if (sceneRef.current.children.length > 0) {
        sceneRef.current.children.forEach((child) => {
          if (child instanceof THREE.Points) {
            child.rotation.y = elapsedTime * 0.1;
            
            // Add subtle floating to the whole object
            child.position.y = Math.sin(elapsedTime * 0.5) * 0.2;
          }
        });
      }
      
      composer.render();
      animationFrameRef.current = requestAnimationFrame(animate);
    };
    
    // Start loading particles (animate will be called after they're ready)
    initParticles();

    // Handle resize
    const handleResize = () => {
      if (!container || !cameraRef.current || !rendererRef.current) return;
      
      const newWidth = container.clientWidth;
      const newHeight = container.clientHeight;
      
      cameraRef.current.aspect = newWidth / newHeight;
      cameraRef.current.updateProjectionMatrix();
      rendererRef.current.setSize(newWidth, newHeight);
      composer.setSize(newWidth, newHeight);
    };

    // Handle mouse move
    const handleMouseMove = (e: MouseEvent) => {
      const rect = container.getBoundingClientRect();
      mouseRef.current.x = ((e.clientX - rect.left) / rect.width - 0.5) * 2;
      mouseRef.current.y = -((e.clientY - rect.top) / rect.height - 0.5) * 2;
    };

    // Handle mouse leave
    const handleMouseLeave = () => {
      mouseRef.current.x = 0;
      mouseRef.current.y = 0;
    };

    window.addEventListener('resize', handleResize);
    container.addEventListener('mousemove', handleMouseMove);
    container.addEventListener('mouseleave', handleMouseLeave);

    // Cleanup
    return () => {
      window.removeEventListener('resize', handleResize);
      container.removeEventListener('mousemove', handleMouseMove);
      container.removeEventListener('mouseleave', handleMouseLeave);
      
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      
      if (rendererRef.current) {
        rendererRef.current.dispose();
        if (container.contains(rendererRef.current.domElement)) {
          container.removeChild(rendererRef.current.domElement);
        }
      }
      
      if (sceneRef.current) {
        sceneRef.current.traverse((object) => {
          if (object instanceof THREE.Mesh || object instanceof THREE.Points) {
            object.geometry.dispose();
            if (object.material instanceof THREE.Material) {
              object.material.dispose();
            }
          }
        });
      }
    };
  }, [logoUrl, fallbackShape, color, backgroundColor, loadSVGLogo, createFallbackGeometry, createParticlesFromGeometry, onLoad, onError]);

  return (
    <div 
      ref={containerRef} 
      className={`relative w-full h-full ${className}`}
      style={{ minHeight: '300px' }}
    >
      {!isLoaded && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/50">
          <div className="w-8 h-8 border-2 border-pandora-cyan/30 border-t-pandora-cyan rounded-full animate-spin" />
        </div>
      )}
    </div>
  );
};

export default ProductParticleVisualizer;
