"use client";

import { useRef, useMemo } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Float, Environment, MeshDistortMaterial } from "@react-three/drei";
import * as THREE from "three";

interface FloatingText3DProps {
  className?: string;
  text?: string;
}

// Create 3D letter blocks as an alternative to Text component
function LetterBlocks({ text = "AGENCY" }: { text?: string }) {
  const groupRef = useRef<THREE.Group>(null);
  const letters = text.split("");

  useFrame((state) => {
    if (groupRef.current) {
      groupRef.current.rotation.y = Math.sin(state.clock.elapsedTime * 0.3) * 0.15;
    }
  });

  const totalWidth = letters.length * 0.7;
  const startX = -totalWidth / 2 + 0.35;

  return (
    <Float speed={2} rotationIntensity={0.2} floatIntensity={0.5}>
      <group ref={groupRef}>
        {letters.map((letter, index) => (
          <LetterBlock
            key={index}
            letter={letter}
            position={[startX + index * 0.7, 0, 0]}
            delay={index * 0.1}
          />
        ))}
      </group>
    </Float>
  );
}

function LetterBlock({
  letter,
  position,
  delay,
}: {
  letter: string;
  position: [number, number, number];
  delay: number;
}) {
  const meshRef = useRef<THREE.Mesh>(null);

  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.position.y =
        position[1] + Math.sin(state.clock.elapsedTime * 2 + delay * 10) * 0.05;
      meshRef.current.rotation.y = Math.sin(state.clock.elapsedTime * 0.5 + delay * 5) * 0.1;
    }
  });

  // Create a simple extruded box for each letter
  return (
    <group position={position}>
      {/* Main block */}
      <mesh ref={meshRef} castShadow>
        <boxGeometry args={[0.5, 0.7, 0.15]} />
        <MeshDistortMaterial
          color="#00d4ff"
          metalness={0.9}
          roughness={0.1}
          distort={0.1}
          speed={2}
        />
      </mesh>
      {/* Glow effect behind */}
      <mesh position={[0, 0, -0.1]}>
        <boxGeometry args={[0.55, 0.75, 0.05]} />
        <meshBasicMaterial color="#ff00ff" transparent opacity={0.3} />
      </mesh>
      {/* Letter label using HTML overlay - handled by CSS */}
    </group>
  );
}

function HeroShape() {
  const meshRef = useRef<THREE.Mesh>(null);

  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.rotation.y = state.clock.elapsedTime * 0.2;
      meshRef.current.rotation.x = Math.sin(state.clock.elapsedTime * 0.3) * 0.1;
    }
  });

  return (
    <Float speed={1.5} rotationIntensity={0.3} floatIntensity={0.6}>
      <mesh ref={meshRef} scale={1.2}>
        <icosahedronGeometry args={[1, 1]} />
        <MeshDistortMaterial
          color="#00d4ff"
          metalness={0.95}
          roughness={0.05}
          distort={0.2}
          speed={3}
          envMapIntensity={2}
        />
      </mesh>
      {/* Inner glow */}
      <mesh scale={0.8}>
        <icosahedronGeometry args={[1, 1]} />
        <meshBasicMaterial color="#a855f7" transparent opacity={0.3} wireframe />
      </mesh>
      {/* Outer ring */}
      <mesh rotation={[Math.PI / 2, 0, 0]} scale={1.8}>
        <torusGeometry args={[1, 0.02, 8, 64]} />
        <meshBasicMaterial color="#00ffff" transparent opacity={0.6} />
      </mesh>
    </Float>
  );
}

function BackgroundParticles() {
  const pointsRef = useRef<THREE.Points>(null);

  const positions = useMemo(() => {
    const pos = new Float32Array(150 * 3);
    for (let i = 0; i < 150; i++) {
      pos[i * 3] = (Math.random() - 0.5) * 20;
      pos[i * 3 + 1] = (Math.random() - 0.5) * 10;
      pos[i * 3 + 2] = (Math.random() - 0.5) * 10 - 5;
    }
    return pos;
  }, []);

  useFrame((state) => {
    if (pointsRef.current) {
      pointsRef.current.rotation.y = state.clock.elapsedTime * 0.02;
    }
  });

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          count={150}
          array={positions}
          itemSize={3}
        />
      </bufferGeometry>
      <pointsMaterial
        size={0.05}
        color="#a855f7"
        transparent
        opacity={0.6}
        sizeAttenuation
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}

export function FloatingText3D({ className = "", text = "AGENCY" }: FloatingText3DProps) {
  return (
    <div className={`w-full h-full min-h-[300px] bg-slate-950 rounded-xl overflow-hidden relative ${className}`}>
      {/* 3D Canvas */}
      <Canvas
        camera={{ position: [0, 0, 5], fov: 50 }}
        gl={{ antialias: true, alpha: true }}
      >
        <color attach="background" args={["#0a0a1a"]} />
        <ambientLight intensity={0.2} />
        <pointLight position={[5, 5, 5]} intensity={2} color="#00d4ff" />
        <pointLight position={[-5, -5, 5]} intensity={1} color="#ff00ff" />
        <pointLight position={[0, 0, 10]} intensity={0.5} color="#ffffff" />
        <spotLight
          position={[0, 10, 5]}
          angle={0.3}
          penumbra={1}
          intensity={2}
          color="#a855f7"
        />
        <HeroShape />
        <BackgroundParticles />
        <Environment preset="night" />
      </Canvas>

      {/* Overlay text using CSS 3D */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        <div
          className="text-4xl font-bold tracking-widest"
          style={{
            background: "linear-gradient(135deg, #00d4ff 0%, #a855f7 50%, #ff00ff 100%)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            textShadow: "0 0 40px rgba(0, 212, 255, 0.5)",
            transform: "perspective(500px) rotateX(5deg)",
          }}
        >
          {text}
        </div>
      </div>

      {/* Label */}
      <div className="absolute bottom-3 left-0 right-0 text-center">
        <p className="text-cyan-400/40 text-[10px] font-mono tracking-wider">
          3D TYPOGRAPHY
        </p>
      </div>
    </div>
  );
}

export default FloatingText3D;
