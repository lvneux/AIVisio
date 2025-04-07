const API_BASE_URL = 'http://127.0.0.1:8000';

export interface ImageResponse {
    filename: string;
}

export async function generateImage(prompt: string): Promise<ImageResponse> {
    const response = await fetch(`${API_BASE_URL}/generate`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ prompt })
    });

    if (!response.ok) {
        throw new Error('이미지 생성에 실패했습니다');
    }

    return response.json();
}

export function getImageUrl(filename: string): string {
    return `${API_BASE_URL}/proxy-image/${filename}`;
} 