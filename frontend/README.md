# CompAI - Modern React Frontend

A stunning, Flash.co-inspired React frontend for the Deep Research Agent. Features glassmorphism effects, smooth animations, and a premium user experience.

![CompAI](https://img.shields.io/badge/React-18+-blue)
![TypeScript](https://img.shields.io/badge/TypeScript-5+-blue)
![Vite](https://img.shields.io/badge/Vite-5+-purple)

## ✨ Features

- **🎨 Premium Design**: Flash.co-inspired UI with glassmorphism effects and smooth animations
- **⚡ Lightning Fast**: Built with Vite for instant dev server and optimized builds
- **🔒 Type Safe**: Full TypeScript support for better DX and fewer bugs
- **📱 Responsive**: Mobile-first design that works on all devices
- **🎭 Animated**: Framer Motion powered animations for delightful interactions
- **🔄 Real-time Updates**: Live research progress tracking with polling
- **📊 Report Viewer**: Beautiful markdown rendering for research reports

## 🏗️ Architecture

```
frontend/
├── src/
│   ├── components/
│   │   ├── common/          # Reusable components (Button, Input, Card, Loading)
│   │   ├── layout/          # Layout components (Header)
│   │   └── sections/        # Page sections (Hero)
│   ├── pages/               # Route pages (Home, Research, Report, History)
│   ├── services/            # API client
│   ├── styles/              # Design system (tokens, global, utils)
│   └── types/               # TypeScript definitions
├── public/                  # Static assets
└── package.json
```

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ and npm
- Backend API running on `http://localhost:8000` (see backend setup below)

### Installation

1. **Install dependencies**:
   ```bash
   cd frontend
   npm install
   ```

2. **Configure environment** (optional):
   ```bash
   cp .env.example .env.local
   # Edit .env.local if your backend runs on a different port
   ```

3. **Start development server**:
   ```bash
   npm run dev
   ```

4. **Open browser**:
   Navigate to `http://localhost:5173`

## 🎨 Design System

### Color Palette

- **Primary Purple**: `#5A16FF` - Vibrant accent color
- **Background Light**: `#F6F5F4` - Soft off-white
- **Background Dark**: `#000000` - Pure black for contrast sections
- **Glassmorphism**: Semi-transparent backgrounds with 30px blur

### Typography

- **Primary Font**: Inter (sans-serif)
- **Accent Font**: Playfair Display (serif italic for emphasis)
- **Hero Text**: 48px - 106px (responsive)
- **Body Text**: 18px

### Key Design Patterns

- **Pill Shapes**: 100px border-radius for inputs and buttons
- **Glassmorphism**: `backdrop-filter: blur(30px)` with transparency
- **Smooth Transitions**: 300ms ease-in-out
- **High Contrast**: Alternating light and dark sections

## 📁 Project Structure

### Components

#### Common Components
- **Button**: Versatile button with variants (primary, secondary, icon, ghost)
- **Input**: Glassmorphism search input with integrated submit button
- **Card**: Flexible card component with hover effects
- **Loading**: Animated loading spinner

#### Pages
- **Home**: Landing page with hero, features, and how-it-works sections
- **Research**: Real-time research progress tracking
- **Report**: Markdown report viewer with download functionality
- **History**: Grid view of past research reports

### API Integration

The frontend communicates with the FastAPI backend via REST endpoints:

- `POST /api/research` - Submit research request
- `GET /api/research/:id` - Get research status
- `GET /api/reports` - List all reports
- `GET /api/reports/:id` - Get specific report
- `GET /api/reports/:id/download` - Download report

## 🔧 Backend Setup

The frontend requires the FastAPI backend to be running:

1. **Navigate to backend directory**:
   ```bash
   cd ../backend
   ```

2. **Install backend dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Start FastAPI server**:
   ```bash
   python app.py
   ```

The backend will run on `http://localhost:8000`

## 📦 Build for Production

```bash
npm run build
```

The optimized build will be in the `dist/` directory.

### Preview Production Build

```bash
npm run preview
```

## 🛠️ Development

### Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

### Code Style

- TypeScript for type safety
- Functional React components with hooks
- CSS Modules for component-scoped styles
- Framer Motion for animations

## 🎯 User Flows

### 1. Submit Research Request
1. Enter company name in hero search input
2. Optionally add ticker symbol
3. Click submit or press Enter
4. Navigate to research progress page

### 2. Track Research Progress
1. View real-time progress bar (0-100%)
2. See which agent is currently running
3. Watch agent status updates
4. Auto-redirect to report when complete

### 3. View Report
1. See formatted markdown report
2. Download report as .md file
3. Navigate to history or start new research

### 4. Browse History
1. View grid of past reports
2. Click any report to view details
3. Search and filter (future enhancement)

## 🎨 Design Inspiration

This UI is inspired by [Flash.co](https://home.flash.co/in), featuring:

- Large, centered search input with glassmorphism
- Serif italic accents for brand emphasis
- High contrast dark sections
- Smooth scroll-based animations
- Premium, modern aesthetic

## 📝 Environment Variables

Create a `.env.local` file:

```bash
VITE_API_URL=http://localhost:8000
```

## 🐛 Troubleshooting

### Backend Connection Issues

If you see "Failed to start research":
1. Ensure backend is running on `http://localhost:8000`
2. Check CORS configuration in `backend/app.py`
3. Verify API endpoints are accessible

### Build Errors

If you encounter build errors:
1. Delete `node_modules` and `package-lock.json`
2. Run `npm install` again
3. Clear Vite cache: `rm -rf node_modules/.vite`

## 🚧 Future Enhancements

- [ ] WebSocket support for real-time updates (instead of polling)
- [ ] Dark mode toggle
- [ ] Report search and filtering
- [ ] Export reports as PDF
- [ ] Share reports via link
- [ ] User authentication
- [ ] Saved searches
- [ ] Comparison view for multiple companies

## 📄 License

This project is part of the Deep Research Agent POC.

## 🙏 Acknowledgments

- Design inspiration: [Flash.co](https://home.flash.co/in)
- Icons: Emoji (native)
- Fonts: Google Fonts (Inter, Playfair Display)

---

**Built with** ❤️ using React, TypeScript, Vite, and Framer Motion
