/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                primary: "#00f2ff", // Neon Cyan
                secondary: "#7000ff", // Neon Purple
                dark: "#0a0a0f", // Deep Space Black
                surface: "#12121a", // Slightly lighter black
                accent: "#ff0099", // Neon Pink
            },
        },
    },
    plugins: [],
}
