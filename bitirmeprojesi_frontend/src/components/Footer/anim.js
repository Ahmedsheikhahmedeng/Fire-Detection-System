export const transforms = [                     //Harflerin dağılacağı yönler
    { x: -0.8, y: -0.6, rotationZ: -29 },
    { x: -0.2, y: -0.4, rotationZ: -6 },
    { x: -0.05, y: 0.1, rotationZ: 12 },
    { x: -0.05, y: -0.1, rotationZ: -9 },
    { x: -0.1, y: 0.55, rotationZ: 3 },
    { x: 0, y: -0.1, rotationZ: 9 },
    { x: 0, y: 0.15, rotationZ: -12 },
    { x: 0, y: 0.15, rotationZ: -17 },
    { x: 0, y: -0.65, rotationZ: 9 },
    { x: 0.1, y: 0.4, rotationZ: 12 },
    { x: 0, y: -0.15, rotationZ: -9 },
    { x: 0.2, y: 0.15, rotationZ: 12 },
    { x: 0.8, y: 0.6, rotationZ: 20 }
];

export const disperse = {
    open: (i) => ({                               //Her harf farklı yöne uçar
        x: transforms[i % transforms.length].x + "em",
        y: transforms[i % transforms.length].y + "em",
        rotateZ: transforms[i % transforms.length].rotationZ,

        color: "var(--brand-ember)", 
        scale: 1.2,       //  BÜYÜME
        filter: "blur(0px)",
                                                    //Smooth animasyon
        transition: { duration: 0.6, ease: [0.33, 1, 0.68, 1] },
        zIndex: 2
    }),

    closed: {
        x: 0,
        y: 0,
        rotateZ: 0,

        color: "var(--text-primary)",
        scale: 1,
        filter: "blur(0px)",

        transition: { duration: 0.6, ease: [0.33, 1, 0.68, 1] },
        zIndex: 0
    }
};
