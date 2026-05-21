export const perspective = {
  initial: {
    opacity: 0,
    y: 26,
  },
  enter: (i) => ({
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.42,
      delay: 0.1 + i * 0.05,
      ease: [0.215, 0.61, 0.355, 1],
    },
  }),
  exit: {
    opacity: 0,
    y: 12,
    transition: {
      duration: 0.18,
      ease: "easeIn",
    },
  },
};
