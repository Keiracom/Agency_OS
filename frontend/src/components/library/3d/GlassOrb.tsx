"use client";

import { useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { MeshTransmissionMaterial, Environment, Float } from "@react-three/drei";
import * as THREE from "three";

interface GlassOrbProps {
  className?: string;
}

function Orb() {
  const meshRef = useRef<THREE.Mesh>(null);

  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.rotation.y += 0.003;
      meshRef.current.rotation.x = Math.sin(state.clock.elapsedTime * 0.2) * 0.1;
    }
  });

  return (
    <Float speed={1.5} rotationIntensity={0.3} floatIntensity={0.8}>
      <mesh ref={meshRef} scale={2}>
        <sphereGeometry args={[1, 64, 64]} />
        <MeshTransmissionMaterial
          backside
          samples={16}
          thickness={0.5}
          chromaticAberration={0.5}
          anisotropy={0.3}
          distortion={0.2}
          distortionScale={0.3}
          temporalDistortion={0.1}
          iridescence={1}
          iridescenceIOR={1}
          iridescenceThicknessRange={[0, 1400]}
          clearcoat={1}
          attenuationDistance={0.5}
          attenuationColor="#00d4ff"
          color="#ffffff"
          transmission={1}
          roughness={0}
          ior={1.5}
        />
      </mesh>
    </Float>
  );
}

function InnerGlow() {
  const meshRef = useRef<THREE.Mesh>(null);

  useFrame((state) => {
    if (meshRef.current) {
      const scale = 0.5 + Math.sin(state.clock.elapsedTime * 2) * 0.1;
      meshRef.current.scale.setScalar(scale);
    }
  });

  return (
    <mesh ref={meshRef} scale={0.5}>
      <sphereGeometry args={[1, 32, 32]} />
      <meshBasicMaterial color="#ff00ff" transparent opacity={0.6} />
    </mesh>
  );
}

function CoreLight() {
  return (
    <mesh scale={0.2}>
      <sphereGeometry args={[1, 16, 16]} />
      <meshBasicMaterial color="#00ffff" transparent opacity={0.9} />
    </mesh>
  );
}

export function GlassOrb({ className = "" }: GlassOrbProps) {
  return (
    <div className={`w-full h-full min-h-[300px] bg-slate-950 rounded-xl overflow-hidden ${className}`}>
      <Canvas
        camera={{ position: [0, 0, 6], fov: 45 }}
        gl={{ antialias: true, alpha: true }}
      >
        <color attach="background" args={["#0a0a1a"]} />
        <ambientLight intensity={0.1} />
        <pointLight position={[10, 10, 10]} intensity={2} color="#00d4ff" />
        <pointLight position={[-10, -10, -10]} intensity={1} color="#ff00ff" />
        <pointLight position={[0, 0, 5]} intensity={0.5} color="#ffffff" />
        <spotLight
          position={[0, 10, 0]}
          angle={0.3}
          penumbra={1}
          intensity={2}
          color="#00ffff"
        />
        <Orb />
        <InnerGlow />
        <CoreLight />
        <Environment preset="night" />
      </Canvas>
    </div>
  );
}

export default GlassOrb;
