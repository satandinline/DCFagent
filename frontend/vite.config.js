import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';
export default defineConfig({
    plugins: [
        react(),
        // 禁用热更新，每次完全重载页面
        {
            name: 'full-reload-on-save',
            handleHotUpdate({ server, file }) {
                // 任何文件保存都触发完整页面重载
                if (file.includes('src/')) {
                    server.ws.send({ type: 'full-reload' });
                }
            }
        }
    ],
    resolve: {
        alias: {
            '@': path.resolve(__dirname, './src'),
        },
    },
    server: {
        port: 3000,
        // 禁用HTTP缓存
        headers: {
            'Cache-Control': 'no-cache, no-store, must-revalidate',
        },
        proxy: {
            '/api': {
                target: 'http://localhost:5050',
                changeOrigin: true,
            },
        },
    },
});
