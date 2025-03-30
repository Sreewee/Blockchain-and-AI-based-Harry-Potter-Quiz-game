// Initialize animation when page loads
document.addEventListener('DOMContentLoaded', () => {
  // Initial fade-in and float-up animation
  gsap.to(".hogwarts-text", {
    duration: 2,
    opacity: 1,
    y: -20,
    ease: "power2.out",
    textShadow: "0 0 20px #f0c75e, 0 0 30px #f0c75e", // Enhanced glow
    onComplete: addFloatEffect // Start floating effect after initial animation
  });
});

// Continuous floating effect
function addFloatEffect() {
  gsap.to(".hogwarts-text", {
    duration: 3,
    y: 20,
    repeat: -1, // Infinite loop
    yoyo: true  // Smooth reverse animation
  });
}