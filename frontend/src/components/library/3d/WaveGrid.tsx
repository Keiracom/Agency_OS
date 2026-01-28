"use client";

import { useRef, useMemo } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import * as THREE from "three";

interface WaveGridProps {
  className?: string;
  wireframe?: boolean;
  resolution?: number;
}

function Wave({ wireframe = false, resolution = 64 }: { wireframe?: boolean; resolution?: number }) {
  const meshRef = useRef<THREE.Mesh>(null);
  const geometryRef = useRef<THREE.PlaneGeometry>(null);

  const { positions, colors } = useMemo(() => {
    const size = resolution + 1;
    const positions = new Float32Array(size * size * 3);
    const colors = new Float32Array(size * size * 3);

    const cyanColor = new THREE.Color("#00d4ff");
    const purpleColor = new THREE.Color("#a855f7");
    const pinkColor = new THREE.Color("#ff00ff");

    for (let i = 0; i < size; i++) {
      for (let j = 0; j < size; j++) {
        const index = (i * size + j) * 3;
        // Initial positions will be updated in useFrame
        positions[index] = (j / resolution - 0.5) * 10;
        positions[index + 1] = 0;
        positions[index + 2] = (i / resolution - 0.5) * 10;

        // Gradient colors
        const t = j / resolution;
        let color: THREE.Color;
        if (t < 0.5) {
          color = cyanColor.clone().lerp(purpleColor, t * 2);
        } else {
          color = purpleColor.clone().lerp(pinkColor, (t - 0.5) * 2);
        }

        colors[index] = color.r;
        colors[index + 1] = color.g;
        colors[index + 2] = color.b;
      }
    }

    return { positions, colors };
  }, [resolution]);

  useFrame((state) => {
    if (meshRef.current && geometryRef.current) {
      const time = state.clock.elapsedTime;
      const positionAttribute = geometryRef.current.attributes.position;
      const size = resolution + 1;

      for (let i = 0; i < size; i++) {
        for (let j = 0; j < size; j++) {
          const index = i * size + j;
          const x = (j / resolution - 0.5) * 10;
          const z = (i / resolution - 0.5) * 10;

          // Multiple wave functions for complex motion
          const wave1 = Math.sin(x * 0.5 + time) * 0.5;
          const wave2 = Math.sin(z * 0.3 + time * 0.8) * 0.3;
          const wave3 = Math.sin((x + z) * 0.4 + time * 1.2) * 0.2;
          const ripple = Math.sin(Math.sqrt(x * x + z * z) * 0.8 - time * 2) * 0.3;

          positionAttribute.setY(index, wave1 + wave2 + wave3 + ripple);
        }
      }

      positionAttribute.needsUpdate = true;
      geometryRef.current.computeVertexNormals();

      // Slow rotation
      meshRef.current.rotation.z = Math.sin(time * 0.1) * 0.05;
    }
  });

  return (
    <mesh ref={meshRef} rotation={[-Math.PI / 3, 0, 0]} position={[0, -1, 0]}>
      <planeGeometry ref={geometryRef} args={[10, 10, resolution, resolution]}>
        <bufferAttribute
          attach="attributes-color"
          count={colors.length / 3}
          array={colors}
          itemSize={3}
        />
      </planeGeometry>
      <meshStandardMaterial
        vertexColors
        wireframe={wireframe}
        side={THREE.DoubleSide}
        metalness={0.8}
        roughness={0.2}
        transparent
        opacity={wireframe ? 0.8 : 1}
      />
    </mesh>
  );
}

function GlowingEdges() {
  return (
    <>
      {/* Bottom glow line */}
      <mesh position={[0, -2.5, -3]} rotation={[-Math.PI / 3, 0, 0]}>
        <planeGeometry args={[12, 0.1]} />
        <meshBasicMaterial color="#00d4ff" transparent opacity={0.5} />
      </mesh>
      {/* Side glow lines */}
      <mesh position={[-5.5, -1.5, 0]} rotation={[-Math.PI / 3, 0, Math.PI / 2]}>
        <planeGeometry args={[8, 0.05]} />
        <meshBasicMaterial color="#ff00ff" transparent opacity={0.3} />
      </mesh>
      <mesh position={[5.5, -1.5, 0]} rotation={[-Math.PI / 3, 0, Math.PI / 2]}>
        <planeGeometry args={[8, 0.05]} />
        <meshBasicMaterial color="#ff00ff" transparent opacity={0.3} />
      </mesh>
    </>
  );
}

export function WaveGrid({ className = "", wireframe = false, resolution = 64 }: WaveGridProps) {
  return (
    <div className={`w-full h-full min-h-[300px] bg-slate-950 rounded-xl overflow-hidden ${className}`}>
      <Canvas
        camera={{ position: [0, 3, 8], fov: 50 }}
        gl={{ antialias: true, alpha: true }}
      >
        <color attach="background" args={["#0a0a1a"]} />
        <ambientLight intensity={0.2} />
        <pointLight position={[0, 10, 0]} intensity={2} color="#00d4ff" />
        <pointLight position={[-5, 5, 5]} intensity={1} color="#ff00ff" />
        <pointLight position={[5, 5, 5]} intensity={1} color="#a855f7" />
        <directionalLight position={[0, 5, 5]} intensity={0.5} color="#ffffff" />
        <Wave wireframe={wireframe} resolution={resolution} />
        <GlowingEdges />
        <fog attach="fog" args={["#0a0a1a", 5, 20]} />
      </Canvas>
    </div>
  );
}

export default WaveGrid;
