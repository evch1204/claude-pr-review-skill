export interface Author { id: string; name: string; avatarUrl: string }
export interface Comment { id: string; postId: string; author: Author; body: string; createdAt: string }
