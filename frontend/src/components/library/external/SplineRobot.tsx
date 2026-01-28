"use client";

import { useRef, useMemo } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Float, MeshDistortMaterial, Environment } from "@react-three/drei";
import * as THREE from "three";

interface SplineRobotProps {
  className?: string;
}

// Robot head component
function RobotHead() {
  const groupRef = useRef<THREE.Group>(null);
  const eyeLeftRef = useRef<THREE.Mesh>(null);
  const eyeRightRef = useRef<THREE.Mesh>(null);

  useFrame((state) => {
    if (groupRef.current) {
      groupRef.current.rotation.y = Math.sin(state.clock.elapsedTime * 0.5) * 0.3;
      groupRef.current.rotation.x = Math.sin(state.clock.elapsedTime * 0.3) * 0.1;
    }
    // Eye glow animation
    if (eyeLeftRef.current && eyeRightRef.current) {
      const intensity = 0.5 + Math.sin(state.clock.elapsedTime * 2) * 0.3;
      (eyeLeftRef.current.material as THREE.MeshBasicMaterial).opacity = intensity;
      (eyeRightRef.current.material as THREE.MeshBasicMaterial).opacity = intensity;
    }
  });

  return (
    <Float speed={2} rotationIntensity={0.2} floatIntensity={0.5}>
      <group ref={groupRef}>
        {/* Main head */}
        <mesh castShadow>
          <boxGeometry args={[1.2, 1.4, 1]} />
          <MeshDistortMaterial
            color="#8b5cf6"
            metalness={0.9}
            roughness={0.1}
            distort={0.05}
            speed={2}
          />
        </mesh>

        {/* Visor/face plate */}
        <mesh position={[0, 0.1, 0.51]}>
          <boxGeometry args={[1, 0.4, 0.05]} />
          <meshStandardMaterial color="#0a0a1a" metalness={0.95} roughness={0.1} />
        </mesh>

        {/* Left eye */}
        <mesh ref={eyeLeftRef} position={[-0.25, 0.1, 0.54]}>
          <circleGeometry args={[0.12, 32]} />
          <meshBasicMaterial color="#00ffff" transparent opacity={0.8} />
        </mesh>

        {/* Right eye */}
        <mesh ref={eyeRightRef} position={[0.25, 0.1, 0.54]}>
          <circleGeometry args={[0.12, 32]} />
          <meshBasicMaterial color="#00ffff" transparent opacity={0.8} />
        </mesh>

        {/* Antenna */}
        <mesh position={[0, 0.9, 0]}>
          <cylinderGeometry args={[0.03, 0.03, 0.4, 8]} />
          <meshStandardMaterial color="#a855f7" metalness={0.8} roughness={0.2} />
        </mesh>
        <mesh position={[0, 1.15, 0]}>
          <sphereGeometry args={[0.08, 16, 16]} />
          <meshBasicMaterial color="#ff00ff" />
        </mesh>

        {/* Ear pieces */}
        <mesh position={[-0.7, 0.1, 0]}>
          <boxGeometry args={[0.2, 0.4, 0.6]} />
          <meshStandardMaterial color="#7c3aed" metalness={0.9} roughness={0.1} />
        </mesh>
        <mesh position={[0.7, 0.1, 0]}>
          <boxGeometry args={[0.2, 0.4, 0.6]} />
          <meshStandardMaterial color="#7c3aed" metalness={0.9} roughness={0.1} />
        </mesh>

        {/* Neck */}
        <mesh position={[0, -0.9, 0]}>
          <cylinderGeometry args={[0.25, 0.35, 0.4, 8]} />
          <meshStandardMaterial color="#6d28d9" metalness={0.85} roughness={0.15} />
        </mesh>

        {/* Shoulder hint */}
        <mesh position={[0, -1.2, 0]}>
          <boxGeometry args={[1.8, 0.3, 0.8]} />
          <MeshDistortMaterial
            color="#5b21b6"
            metalness={0.9}
            roughness={0.1}
            distort={0.02}
            speed={1}
          />
        </mesh>
      </group>
    </Float>
  );
}

// Floating particles around robot
function RobotParticles() {
  const pointsRef = useRef<THREE.Points>(null);

  const positions = useMemo(() => {
    const pos = new Float32Array(100 * 3);
    for (let i = 0; i < 100; i++) {
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.random() * Math.PI;
      const r = 2 + Math.random() * 2;
      pos[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      pos[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta) - 0.5;
      pos[i * 3 + 2] = r * Math.cos(phi);
    }
    return pos;
  }, []);

  useFrame((state) => {
    if (pointsRef.current) {
      pointsRef.current.rotation.y = state.clock.elapsedTime * 0.05;
    }
  });

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          count={100}
          array={positions}
          itemSize={3}
        />
      </bufferGeometry>
      <pointsMaterial
        size={0.04}
        color="#a855f7"
        transparent
        opacity={0.6}
        sizeAttenuation
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}

// Energy rings
function EnergyRings() {
  const ring1Ref = useRef<THREE.Mesh>(null);
  const ring2Ref = useRef<THREE.Mesh>(null);

  useFrame((state) => {
    if (ring1Ref.current) {
      ring1Ref.current.rotation.x = state.clock.elapsedTime * 0.5;
      ring1Ref.current.rotation.z = state.clock.elapsedTime * 0.3;
    }
    if (ring2Ref.current) {
      ring2Ref.current.rotation.x = -state.clock.elapsedTime * 0.4;
      ring2Ref.current.rotation.y = state.clock.elapsedTime * 0.2;
    }
  });

  return (
    <>
      <mesh ref={ring1Ref} position={[0, 0, 0]}>
        <torusGeometry args={[1.8, 0.02, 8, 64]} />
        <meshBasicMaterial color="#8b5cf6" transparent opacity={0.4} />
      </mesh>
      <mesh ref={ring2Ref} position={[0, 0, 0]}>
        <torusGeometry args={[2.2, 0.015, 8, 64]} />
        <meshBasicMaterial color="#00ffff" transparent opacity={0.3} />
      </mesh>
    </>
  );
}

export function SplineRobot({ className }: SplineRobotProps) {
  return (
    <div
      className={`relative w-full h-full min-h-[300px] bg-slate-950 rounded-xl overflow-hidden ${className || ""}`}
    >
      {/* Background gradient */}
      <div className="absolute inset-0 bg-gradient-to-br from-slate-950 via-purple-950/20 to-slate-950" />

      {/* 3D Canvas */}
      <Canvas
        camera={{ position: [0, 0, 4], fov: 50 }}
        gl={{ antialias: true, alpha: true }}
      >
        <color attach="background" args={["#0a0a1a"]} />
        <ambientLight intensity={0.3} />
        <pointLight position={[5, 5, 5]} intensity={1.5} color="#8b5cf6" />
        <pointLight position={[-5, -5, 5]} intensity={1} color="#00ffff" />
        <spotLight
          position={[0, 5, 3]}
          angle={0.4}
          penumbra={1}
          intensity={1.5}
          color="#a855f7"
        />
        <RobotHead />
        <RobotParticles />
        <EnergyRings />
        <Environment preset="night" />
      </Canvas>

      {/* Corner decorations */}
      <div className="absolute top-3 left-3 w-6 h-6 border-l-2 border-t-2 border-purple-500/50 pointer-events-none" />
      <div className="absolute top-3 right-3 w-6 h-6 border-r-2 border-t-2 border-purple-500/50 pointer-events-none" />
      <div className="absolute bottom-3 left-3 w-6 h-6 border-l-2 border-b-2 border-purple-500/50 pointer-events-none" />
      <div className="absolute bottom-3 right-3 w-6 h-6 border-r-2 border-b-2 border-purple-500/50 pointer-events-none" />

      {/* Glow effects */}
      <div className="absolute top-0 left-0 w-16 h-16 bg-purple-500/10 blur-2xl pointer-events-none" />
      <div className="absolute bottom-0 right-0 w-16 h-16 bg-cyan-500/10 blur-2xl pointer-events-none" />

      {/* Label */}
      <div className="absolute bottom-4 left-0 right-0 text-center pointer-events-none">
        <p className="text-purple-400/40 text-[10px] font-mono tracking-wider">
          3D ROBOT HEAD
        </p>
      </div>
    </div>
  );
}

export default SplineRobot;
