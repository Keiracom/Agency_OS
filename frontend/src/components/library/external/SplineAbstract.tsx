"use client";

import { useRef, useMemo } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Float, MeshDistortMaterial, Environment, MeshTransmissionMaterial } from "@react-three/drei";
import * as THREE from "three";

interface SplineAbstractProps {
  className?: string;
}

// Abstract floating shapes
function AbstractShapes() {
  const group1Ref = useRef<THREE.Group>(null);
  const group2Ref = useRef<THREE.Group>(null);
  const torusRef = useRef<THREE.Mesh>(null);

  useFrame((state) => {
    if (group1Ref.current) {
      group1Ref.current.rotation.y = state.clock.elapsedTime * 0.2;
      group1Ref.current.rotation.x = Math.sin(state.clock.elapsedTime * 0.3) * 0.2;
    }
    if (group2Ref.current) {
      group2Ref.current.rotation.y = -state.clock.elapsedTime * 0.15;
      group2Ref.current.rotation.z = Math.cos(state.clock.elapsedTime * 0.2) * 0.15;
    }
    if (torusRef.current) {
      torusRef.current.rotation.x = state.clock.elapsedTime * 0.4;
      torusRef.current.rotation.y = state.clock.elapsedTime * 0.2;
    }
  });

  return (
    <>
      {/* Central glass sphere */}
      <Float speed={1.5} rotationIntensity={0.3} floatIntensity={0.4}>
        <mesh scale={0.8}>
          <icosahedronGeometry args={[1, 2]} />
          <MeshDistortMaterial
            color="#00d4ff"
            metalness={0.9}
            roughness={0.1}
            distort={0.3}
            speed={3}
            envMapIntensity={1.5}
          />
        </mesh>
        {/* Inner core */}
        <mesh scale={0.5}>
          <dodecahedronGeometry args={[1, 0]} />
          <meshBasicMaterial color="#ff00ff" wireframe transparent opacity={0.6} />
        </mesh>
      </Float>

      {/* Orbiting spheres group 1 */}
      <group ref={group1Ref}>
        {[0, 1, 2, 3].map((i) => (
          <mesh
            key={`orb1-${i}`}
            position={[
              Math.cos((i / 4) * Math.PI * 2) * 1.8,
              Math.sin((i / 4) * Math.PI * 2) * 0.3,
              Math.sin((i / 4) * Math.PI * 2) * 1.8,
            ]}
          >
            <sphereGeometry args={[0.15, 16, 16]} />
            <meshStandardMaterial
              color={i % 2 === 0 ? "#00ffff" : "#ff00ff"}
              emissive={i % 2 === 0 ? "#00ffff" : "#ff00ff"}
              emissiveIntensity={0.5}
              metalness={0.8}
              roughness={0.2}
            />
          </mesh>
        ))}
      </group>

      {/* Orbiting spheres group 2 */}
      <group ref={group2Ref}>
        {[0, 1, 2, 3, 4, 5].map((i) => (
          <mesh
            key={`orb2-${i}`}
            position={[
              Math.cos((i / 6) * Math.PI * 2) * 2.5,
              Math.sin((i / 6) * Math.PI * 2 + 1) * 0.5,
              Math.sin((i / 6) * Math.PI * 2) * 2.5,
            ]}
          >
            <octahedronGeometry args={[0.1, 0]} />
            <meshBasicMaterial
              color="#a855f7"
              transparent
              opacity={0.8}
            />
          </mesh>
        ))}
      </group>

      {/* Animated torus */}
      <mesh ref={torusRef} scale={1.2}>
        <torusGeometry args={[1.5, 0.02, 8, 100]} />
        <meshBasicMaterial color="#00ffff" transparent opacity={0.5} />
      </mesh>

      {/* Secondary torus */}
      <mesh rotation={[Math.PI / 2, 0, 0]} scale={1.2}>
        <torusGeometry args={[1.8, 0.015, 8, 100]} />
        <meshBasicMaterial color="#a855f7" transparent opacity={0.3} />
      </mesh>
    </>
  );
}

// Floating geometric shapes
function FloatingGeometry() {
  const meshRefs = useRef<THREE.Mesh[]>([]);

  useFrame((state) => {
    meshRefs.current.forEach((mesh, i) => {
      if (mesh) {
        mesh.rotation.x = state.clock.elapsedTime * (0.2 + i * 0.1);
        mesh.rotation.y = state.clock.elapsedTime * (0.3 + i * 0.05);
        mesh.position.y = Math.sin(state.clock.elapsedTime + i) * 0.2 + (i - 1) * 1.5;
      }
    });
  });

  const geometries = [
    { geo: <boxGeometry args={[0.3, 0.3, 0.3]} />, pos: [-2, 1, -1] as [number, number, number], color: "#00d4ff" },
    { geo: <tetrahedronGeometry args={[0.25, 0]} />, pos: [2, -0.5, -1] as [number, number, number], color: "#ff00ff" },
    { geo: <octahedronGeometry args={[0.2, 0]} />, pos: [-1.5, -1, 0.5] as [number, number, number], color: "#a855f7" },
  ];

  return (
    <>
      {geometries.map((item, i) => (
        <Float key={i} speed={2 + i * 0.5} rotationIntensity={0.5} floatIntensity={0.3}>
          <mesh
            ref={(el) => { if (el) meshRefs.current[i] = el; }}
            position={item.pos}
          >
            {item.geo}
            <meshStandardMaterial
              color={item.color}
              metalness={0.9}
              roughness={0.1}
              emissive={item.color}
              emissiveIntensity={0.2}
            />
          </mesh>
        </Float>
      ))}
    </>
  );
}

// Background particles
function AbstractParticles() {
  const pointsRef = useRef<THREE.Points>(null);

  const positions = useMemo(() => {
    const pos = new Float32Array(200 * 3);
    for (let i = 0; i < 200; i++) {
      pos[i * 3] = (Math.random() - 0.5) * 10;
      pos[i * 3 + 1] = (Math.random() - 0.5) * 10;
      pos[i * 3 + 2] = (Math.random() - 0.5) * 10 - 3;
    }
    return pos;
  }, []);

  useFrame((state) => {
    if (pointsRef.current) {
      pointsRef.current.rotation.y = state.clock.elapsedTime * 0.03;
      pointsRef.current.rotation.x = state.clock.elapsedTime * 0.02;
    }
  });

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          count={200}
          array={positions}
          itemSize={3}
        />
      </bufferGeometry>
      <pointsMaterial
        size={0.03}
        color="#00ffff"
        transparent
        opacity={0.5}
        sizeAttenuation
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}

export function SplineAbstract({ className }: SplineAbstractProps) {
  return (
    <div
      className={`relative w-full h-full min-h-[300px] bg-slate-950 rounded-xl overflow-hidden ${className || ""}`}
    >
      {/* Background gradient */}
      <div className="absolute inset-0 bg-gradient-to-br from-slate-950 via-cyan-950/10 to-slate-950" />

      {/* Subtle grid pattern */}
      <div
        className="absolute inset-0 opacity-5 pointer-events-none"
        style={{
          backgroundImage: `
            linear-gradient(to right, rgba(0, 255, 255, 0.5) 1px, transparent 1px),
            linear-gradient(to bottom, rgba(0, 255, 255, 0.5) 1px, transparent 1px)
          `,
          backgroundSize: "40px 40px",
        }}
      />

      {/* 3D Canvas */}
      <Canvas
        camera={{ position: [0, 0, 5], fov: 50 }}
        gl={{ antialias: true, alpha: true }}
      >
        <color attach="background" args={["#0a0a1a"]} />
        <ambientLight intensity={0.2} />
        <pointLight position={[5, 5, 5]} intensity={1.5} color="#00d4ff" />
        <pointLight position={[-5, -5, 5]} intensity={1} color="#ff00ff" />
        <pointLight position={[0, 0, 5]} intensity={0.5} color="#ffffff" />
        <spotLight
          position={[0, 10, 5]}
          angle={0.3}
          penumbra={1}
          intensity={1}
          color="#a855f7"
        />
        <AbstractShapes />
        <FloatingGeometry />
        <AbstractParticles />
        <Environment preset="night" />
      </Canvas>

      {/* Corner decorations - SVG style */}
      <svg className="absolute top-2 left-2 w-8 h-8 pointer-events-none" viewBox="0 0 32 32">
        <path
          d="M 0 12 L 0 0 L 12 0"
          fill="none"
          stroke="rgba(0, 255, 255, 0.5)"
          strokeWidth="2"
        />
        <circle cx="0" cy="0" r="2" fill="rgba(0, 255, 255, 0.6)" className="animate-pulse" />
      </svg>
      <svg className="absolute top-2 right-2 w-8 h-8 pointer-events-none" viewBox="0 0 32 32">
        <path
          d="M 20 0 L 32 0 L 32 12"
          fill="none"
          stroke="rgba(0, 255, 255, 0.5)"
          strokeWidth="2"
        />
      </svg>
      <svg className="absolute bottom-2 left-2 w-8 h-8 pointer-events-none" viewBox="0 0 32 32">
        <path
          d="M 0 20 L 0 32 L 12 32"
          fill="none"
          stroke="rgba(0, 255, 255, 0.5)"
          strokeWidth="2"
        />
      </svg>
      <svg className="absolute bottom-2 right-2 w-8 h-8 pointer-events-none" viewBox="0 0 32 32">
        <path
          d="M 20 32 L 32 32 L 32 20"
          fill="none"
          stroke="rgba(0, 255, 255, 0.5)"
          strokeWidth="2"
        />
        <circle cx="32" cy="32" r="2" fill="rgba(0, 255, 255, 0.6)" className="animate-pulse" />
      </svg>

      {/* Glow accents */}
      <div className="absolute top-0 left-0 w-24 h-24 bg-cyan-500/5 blur-3xl pointer-events-none" />
      <div className="absolute bottom-0 right-0 w-24 h-24 bg-purple-500/5 blur-3xl pointer-events-none" />

      {/* Label */}
      <div className="absolute bottom-4 left-0 right-0 text-center pointer-events-none">
        <p className="text-cyan-400/40 text-[10px] font-mono tracking-wider">
          ABSTRACT 3D SCENE
        </p>
      </div>
    </div>
  );
}

export default SplineAbstract;
