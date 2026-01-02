# PlanProof React Frontend

Modern React + TypeScript frontend for the PlanProof planning validation system.

## Features

- 🎨 **Material-UI** - Professional, accessible UI components
- ⚡ **Vite** - Lightning-fast development and builds
- 🔒 **TypeScript** - Type-safe code
- 📤 **Drag & Drop Upload** - Intuitive file uploads with progress
- 📊 **Real-time Results** - Live validation results and analytics
- 🔄 **REST API Integration** - Clean API client with Axios

## Quick Start

### Prerequisites
- Node.js 18+ and npm

### Installation

```bash
cd frontend
npm install
```

### Development

```bash
# Start dev server (http://localhost:3000)
npm run dev
```

### Production Build

```bash
npm run build
npm run preview
```

## Project Structure

```
frontend/
├── src/
│   ├── api/          # API client and endpoints
│   ├── components/   # Reusable components
│   ├── pages/        # Page components
│   ├── types/        # TypeScript types
│   ├── App.tsx       # Main app component
│   └── main.tsx      # Entry point
├── public/           # Static assets
├── index.html        # HTML template
├── package.json      # Dependencies
├── tsconfig.json     # TypeScript config
└── vite.config.ts    # Vite config
```

## API Configuration

The frontend connects to the FastAPI backend at `http://localhost:8000` by default.

To change the API URL, edit `.env`:

```
VITE_API_URL=http://your-api-url:8000
```

## Pages

- **New Application** - Upload and validate planning documents
- **My Cases** - View all your planning applications
- **All Runs** - Complete validation run history
- **Results** - Detailed validation results and findings
- **Dashboard** - Analytics and insights

## Technology Stack

- **React 18** - UI library
- **TypeScript** - Type safety
- **Material-UI v5** - Component library
- **Vite** - Build tool
- **React Router v6** - Routing
- **Axios** - HTTP client
- **React Dropzone** - File uploads
- **Recharts** - Data visualization

## Development Tips

### Hot Reload
Vite provides instant hot module replacement (HMR) - your changes appear immediately without full page reload.

### Type Checking
```bash
npm run build  # TypeScript checks run during build
```

### API Proxy
Development server proxies `/api` requests to `http://localhost:8000` to avoid CORS issues.

## Deployment

### Build for Production
```bash
npm run build
```

This creates an optimized build in `dist/` folder.

### Serve Static Build
```bash
npm run preview
```

Or deploy the `dist/` folder to any static hosting service (Netlify, Vercel, S3, etc.).

## vs. Streamlit UI

**Advantages of React Frontend:**
- ✅ Better performance and user experience
- ✅ Full control over UI/UX
- ✅ Professional, responsive design
- ✅ Better error handling
- ✅ Real-time updates
- ✅ Modern development workflow
- ✅ Production-ready

The old Streamlit UI is located in `planproof/ui/` but is now deprecated in favor of this React frontend.
