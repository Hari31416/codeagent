import { v4 as uuidv4 } from 'uuid'

export function getUserId(): string {
    const STORAGE_KEY = 'codeagent_user_id'
    let userId = localStorage.getItem(STORAGE_KEY)

    if (!userId) {
        userId = uuidv4()
        localStorage.setItem(STORAGE_KEY, userId)
    }

    return userId as string
}
