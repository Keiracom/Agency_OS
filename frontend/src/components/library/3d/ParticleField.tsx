"use client";

import { useRef, useMemo } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Points, PointMaterial } from "@react-three/drei";
import * as THREE from "three";

interface ParticleFieldProps {
  className?: string;
  particleCount?: number;
}

function Particles({ count = 500 }: { count?: number }) {
  const pointsRef = useRef<THREE.Points>(null);
  const rotationRef = useRef({ x: 0, y: 0 });

  const [positions, colors] = useMemo(() => {
    const positions = new Float32Array(count * 3);
    const colors = new Float32Array(count * 3);

    const cyanColor = new THREE.Color("#00d4ff");
    const purpleColor = new THREE.Color("#a855f7");
    const pinkColor = new THREE.Color("#ff00ff");

    for (let i = 0; i < count; i++) {
      // Spherical distribution
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      const radius = 2 + Math.random() * 2;

      positions[i * 3] = radius * Math.sin(phi) * Math.cos(theta);
      positions[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta);
      positions[i * 3 + 2] = radius * Math.cos(phi);

      // Color gradient based on position
      const t = (positions[i * 3 + 1] + 4) / 8; // Normalize Y position
      let color: THREE.Color;
      if (t < 0.5) {
        color = cyanColor.clone().lerp(purpleColor, t * 2);
      } else {
        color = purpleColor.clone().lerp(pinkColor, (t - 0.5) * 2);
      }

      colors[i * 3] = color.r;
      colors[i * 3 + 1] = color.g;
      colors[i * 3 + 2] = color.b;
    }

    return [positions, colors];
  }, [count]);

  useFrame((state) => {
    if (pointsRef.current) {
      rotationRef.current.y += 0.002;
      rotationRef.current.x = Math.sin(state.clock.elapsedTime * 0.1) * 0.1;

      pointsRef.current.rotation.y = rotationRef.current.y;
      pointsRef.current.rotation.x = rotationRef.current.x;

      // Subtle pulsing
      const scale = 1 + Math.sin(state.clock.elapsedTime * 0.5) * 0.05;
      pointsRef.current.scale.setScalar(scale);
    }
  });

  return (
    <Points ref={pointsRef} positions={positions} stride={3} frustumCulled={false}>
      <PointMaterial
        transparent
        vertexColors
        size={0.05}
        sizeAttenuation={true}
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
      <bufferAttribute
        attach="geometry-attributes-color"
        count={colors.length / 3}
        array={colors}
        itemSize={3}
      />
    </Points>
  );
}

function CoreGlow() {
  const meshRef = useRef<THREE.Mesh>(null);

  useFrame((state) => {
    if (meshRef.current) {
      const scale = 0.3 + Math.sin(state.clock.elapsedTime * 2) * 0.1;
      meshRef.current.scale.setScalar(scale);
    }
  });

  return (
    <mesh ref={meshRef}>
      <sphereGeometry args={[1, 32, 32]} />
      <meshBasicMaterial color="#00d4ff" transparent opacity={0.2} />
    </mesh>
  );
}

export function ParticleField({ className = "", particleCount = 500 }: ParticleFieldProps) {
  return (
    <div className={`w-full h-full min-h-[300px] bg-slate-950 rounded-xl overflow-hidden ${className}`}>
      <Canvas
        camera={{ position: [0, 0, 8], fov: 50 }}
        gl={{ antialias: true, alpha: true }}
      >
        <color attach="background" args={["#0a0a1a"]} />
        <ambientLight intensity={0.1} />
        <pointLight position={[0, 0, 0]} intensity={1} color="#00d4ff" />
        <Particles count={particleCount} />
        <CoreGlow />
      </Canvas>
    </div>
  );
}

export default ParticleField;
