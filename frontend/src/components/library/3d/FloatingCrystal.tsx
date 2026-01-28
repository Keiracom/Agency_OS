"use client";

import { useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { MeshDistortMaterial, Environment, Float } from "@react-three/drei";
import * as THREE from "three";

function Crystal() {
  const meshRef = useRef<THREE.Mesh>(null);

  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.rotation.y += 0.005;
      meshRef.current.rotation.x = Math.sin(state.clock.elapsedTime * 0.3) * 0.1;
    }
  });

  return (
    <Float speed={2} rotationIntensity={0.5} floatIntensity={1}>
      <mesh ref={meshRef} scale={2}>
        <octahedronGeometry args={[1, 0]} />
        <MeshDistortMaterial
          color="#00d4ff"
          attach="material"
          distort={0.4}
          speed={2}
          roughness={0}
          metalness={0.8}
          envMapIntensity={1}
          clearcoat={1}
          clearcoatRoughness={0}
          transparent
          opacity={0.9}
        />
      </mesh>
    </Float>
  );
}

function InnerGlow() {
  return (
    <mesh scale={1.5}>
      <octahedronGeometry args={[1, 0]} />
      <meshBasicMaterial color="#00ffff" transparent opacity={0.1} wireframe />
    </mesh>
  );
}

export function FloatingCrystal() {
  return (
    <div className="w-full h-full min-h-[300px] bg-slate-950 rounded-xl overflow-hidden">
      <Canvas
        camera={{ position: [0, 0, 5], fov: 45 }}
        gl={{ antialias: true, alpha: true }}
      >
        <color attach="background" args={["#0a0a1a"]} />
        <ambientLight intensity={0.2} />
        <pointLight position={[10, 10, 10]} intensity={1} color="#00d4ff" />
        <pointLight position={[-10, -10, -10]} intensity={0.5} color="#ff00ff" />
        <spotLight
          position={[0, 5, 0]}
          angle={0.3}
          penumbra={1}
          intensity={2}
          color="#00ffff"
        />
        <Crystal />
        <InnerGlow />
        <Environment preset="night" />
      </Canvas>
    </div>
  );
}

export default FloatingCrystal;
