import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { cn } from '@/lib/utils'
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import {
    Trash2,
    UserPlus,
    Shield,
    User as UserIcon,
    RefreshCw,
    Search,
    ArrowLeft
} from 'lucide-react'
import { listUsers, createUser, updateUser, deleteUser } from '@/api/auth'
import type { User, UserCreateRequest, UserUpdateRequest } from '@/types/auth'
import { useAuthStore } from '@/stores/authStore'

// Simple replacement for TableRow since we removed the Table component
const TableRow = ({ children, className, ...props }: any) => (
    <tr className={cn("border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted", className)} {...props}>
        {children}
    </tr>
)

export function UserManagement() {
    const navigate = useNavigate()
    const [users, setUsers] = useState<User[]>([])
    const [isLoading, setIsLoading] = useState(true)
    const [searchQuery, setSearchQuery] = useState('')
    const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false)
    const [isEditDialogOpen, setIsEditDialogOpen] = useState(false)
    const [selectedUser, setSelectedUser] = useState<User | null>(null)

    // Form states
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [fullName, setFullName] = useState('')
    const [role, setRole] = useState<'admin' | 'user'>('user')

    const { user: currentUser } = useAuthStore()

    const fetchUsers = useCallback(async () => {
        setIsLoading(true)
        try {
            const response = await listUsers()
            if (response.success && response.data) {
                setUsers(response.data)
            }
        } catch (error) {
            console.error('Failed to fetch users:', error)
        } finally {
            setIsLoading(false)
        }
    }, [])

    useEffect(() => {
        fetchUsers()
    }, [fetchUsers])

    const handleCreateUser = async (e: React.FormEvent) => {
        e.preventDefault()
        try {
            const request: UserCreateRequest = {
                email,
                password,
                full_name: fullName,
                role
            }
            const response = await createUser(request)
            if (response.success) {
                setIsCreateDialogOpen(false)
                resetForm()
                fetchUsers()
            }
        } catch (error) {
            console.error('Failed to create user:', error)
        }
    }

    const handleUpdateUser = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!selectedUser) return
        try {
            const request: UserUpdateRequest = {
                email,
                full_name: fullName,
                role
            }
            if (password) request.password = password

            const response = await updateUser(selectedUser.user_id, request)
            if (response.success) {
                setIsEditDialogOpen(false)
                resetForm()
                fetchUsers()
            }
        } catch (error) {
            console.error('Failed to update user:', error)
        }
    }

    const handleDeleteUser = async (userId: string) => {
        if (userId === currentUser?.user_id) {
            alert("You cannot delete yourself.")
            return
        }

        if (confirm('Are you sure you want to delete this user? This action cannot be undone.')) {
            try {
                await deleteUser(userId)
                fetchUsers()
            } catch (error) {
                console.error('Failed to delete user:', error)
            }
        }
    }

    const resetForm = () => {
        setEmail('')
        setPassword('')
        setFullName('')
        setRole('user')
        setSelectedUser(null)
    }

    const openEditDialog = (user: User) => {
        setSelectedUser(user)
        setEmail(user.email)
        setFullName(user.full_name || '')
        setRole(user.role)
        setPassword('')
        setIsEditDialogOpen(true)
    }

    const filteredUsers = users.filter(u =>
        u.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (u.full_name?.toLowerCase() || '').includes(searchQuery.toLowerCase())
    )

    return (
        <div className="flex flex-col h-full bg-background p-6 overflow-auto">
            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-4">
                    <Button variant="ghost" size="icon" onClick={() => navigate('/')}>
                        <ArrowLeft className="h-5 w-5" />
                    </Button>
                    <div>
                        <h1 className="text-3xl font-bold tracking-tight">User Management</h1>
                        <p className="text-muted-foreground">
                            Manage your organization's users and their roles.
                        </p>
                    </div>
                </div>
                <div className="flex gap-2">
                    <Button variant="outline" size="icon" onClick={fetchUsers} disabled={isLoading}>
                        <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
                    </Button>
                    <Button onClick={() => setIsCreateDialogOpen(true)}>
                        <UserPlus className="mr-2 h-4 w-4" />
                        Add User
                    </Button>
                </div>
            </div>

            <div className="flex items-center gap-2 mb-4">
                <div className="relative flex-1 max-w-sm">
                    <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                    <Input
                        placeholder="Search users..."
                        className="pl-8"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                    />
                </div>
            </div>

            <div className="rounded-md border bg-card overflow-hidden">
                <table className="w-full text-sm">
                    <thead className="bg-muted/50 border-b">
                        <tr>
                            <th className="h-10 px-4 text-left font-medium text-muted-foreground">User</th>
                            <th className="h-10 px-4 text-left font-medium text-muted-foreground">Email</th>
                            <th className="h-10 px-4 text-left font-medium text-muted-foreground">Role</th>
                            <th className="h-10 px-4 text-left font-medium text-muted-foreground">Status</th>
                            <th className="h-10 px-4 text-right font-medium text-muted-foreground">Actions</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y">
                        {filteredUsers.length === 0 ? (
                            <tr>
                                <td colSpan={5} className="h-24 text-center text-muted-foreground">
                                    {isLoading ? 'Loading users...' : 'No users found.'}
                                </td>
                            </tr>
                        ) : (
                            filteredUsers.map((u) => (
                                <TableRow key={u.user_id} className="hover:bg-muted/50 transition-colors">
                                    <td className="p-4 align-middle">
                                        <div className="flex items-center gap-2">
                                            <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-primary font-bold overflow-hidden">
                                                {u.full_name ? u.full_name.charAt(0).toUpperCase() : u.email.charAt(0).toUpperCase()}
                                            </div>
                                            <span className="font-medium">{u.full_name || 'N/A'}</span>
                                        </div>
                                    </td>
                                    <td className="p-4 align-middle">{u.email}</td>
                                    <td className="p-4 align-middle">
                                        <Badge variant={u.role === 'admin' ? 'default' : 'secondary'} className="gap-1">
                                            {u.role === 'admin' ? (
                                                <Shield className="h-3 w-3" />
                                            ) : (
                                                <UserIcon className="h-3 w-3" />
                                            )}
                                            {u.role}
                                        </Badge>
                                    </td>
                                    <td className="p-4 align-middle">
                                        <Badge variant={u.is_active ? 'outline' : 'destructive'} className={u.is_active ? 'text-green-600 border-green-200' : ''}>
                                            {u.is_active ? 'Active' : 'Inactive'}
                                        </Badge>
                                    </td>
                                    <td className="p-4 align-middle text-right">
                                        <div className="flex justify-end gap-2">
                                            <Button variant="ghost" size="sm" onClick={() => openEditDialog(u)}>
                                                Edit
                                            </Button>
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                className="text-destructive hover:text-destructive"
                                                onClick={() => handleDeleteUser(u.user_id)}
                                                disabled={u.user_id === currentUser?.user_id}
                                            >
                                                <Trash2 className="h-4 w-4" />
                                            </Button>
                                        </div>
                                    </td>
                                </TableRow>
                            ))
                        )}
                    </tbody>
                </table>
            </div>

            {/* Create Dialog */}
            <Dialog open={isCreateDialogOpen} onOpenChange={(open) => {
                setIsCreateDialogOpen(open);
                if (!open) resetForm();
            }}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Create New User</DialogTitle>
                        <DialogDescription>
                            Add a new user to your organization. They will be able to log in immediately.
                        </DialogDescription>
                    </DialogHeader>
                    <form onSubmit={handleCreateUser}>
                        <div className="space-y-4 py-4">
                            <div className="space-y-2">
                                <Label htmlFor="email">Email address *</Label>
                                <Input
                                    id="email"
                                    type="email"
                                    placeholder="name@example.com"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    required
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="fullName">Full Name</Label>
                                <Input
                                    id="fullName"
                                    placeholder="John Doe"
                                    value={fullName}
                                    onChange={(e) => setFullName(e.target.value)}
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="password">Initial Password *</Label>
                                <Input
                                    id="password"
                                    type="password"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    required
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="role">Role</Label>
                                <select
                                    id="role"
                                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                                    value={role}
                                    onChange={(e) => setRole(e.target.value as 'admin' | 'user')}
                                >
                                    <option value="user">User</option>
                                    <option value="admin">Admin</option>
                                </select>
                            </div>
                        </div>
                        <DialogFooter>
                            <Button type="button" variant="outline" onClick={() => {
                                setIsCreateDialogOpen(false);
                                resetForm();
                            }}>
                                Cancel
                            </Button>
                            <Button type="submit">Create User</Button>
                        </DialogFooter>
                    </form>
                </DialogContent>
            </Dialog>

            {/* Edit Dialog */}
            <Dialog open={isEditDialogOpen} onOpenChange={(open) => {
                setIsEditDialogOpen(open);
                if (!open) resetForm();
            }}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Edit User</DialogTitle>
                        <DialogDescription>
                            Update user details or change their role.
                        </DialogDescription>
                    </DialogHeader>
                    <form onSubmit={handleUpdateUser}>
                        <div className="space-y-4 py-4">
                            <div className="space-y-2">
                                <Label htmlFor="edit-email">Email address</Label>
                                <Input
                                    id="edit-email"
                                    type="email"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    required
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="edit-fullName">Full Name</Label>
                                <Input
                                    id="edit-fullName"
                                    value={fullName}
                                    onChange={(e) => setFullName(e.target.value)}
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="edit-password">New Password (leave blank to keep current)</Label>
                                <Input
                                    id="edit-password"
                                    type="password"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    placeholder="••••••••"
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="edit-role">Role</Label>
                                <select
                                    id="edit-role"
                                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                                    value={role}
                                    onChange={(e) => setRole(e.target.value as 'admin' | 'user')}
                                >
                                    <option value="user">User</option>
                                    <option value="admin">Admin</option>
                                </select>
                            </div>
                        </div>
                        <DialogFooter>
                            <Button type="button" variant="outline" onClick={() => {
                                setIsEditDialogOpen(false);
                                resetForm();
                            }}>
                                Cancel
                            </Button>
                            <Button type="submit">Update User</Button>
                        </DialogFooter>
                    </form>
                </DialogContent>
            </Dialog>
        </div>
    )
}
