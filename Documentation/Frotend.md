# 📊 Project Documentation

## 🔍 Overview
This is a React-based Single Page Application (SPA) built with Vite, focused on financial backtesting and portfolio analytics. The project uses modern JavaScript/JSX with a component-driven architecture and a modern design system.

## ⚡ Technology Stack
- **Frontend**: React with JSX 
- **Build Tool**: Vite 
- **Package Manager**: pnpm 
- **HTTP Client**: Axios 
- **Styling**: Tailwind CSS 
- **UI Components**: shadcn/ui 

## 📁 Project Structure

```
.
├── dist/                    # Production build output 
├── lib/                     # External libraries 
├── node_modules/            # Dependencies 
├── public/                  # Static assets 
├── src/                     # Source code 
│   ├── assets/              # Images, fonts, icons 
│   ├── components/          # Reusable UI components 
│   │   └── ui/              # shadcn/ui components 
│   ├── hooks/               # Custom React hooks
│   ├── layout/              # Layout components 
│   ├── lib/                 # Utilities and API clients 
│   │   └── utils.js         # shadcn/ui utility functions 
│   ├── pages/               # Page-level components 
│   │   ├── backtesting/     # Backtesting feature 
│   │   └── home/            # Landing page 
│   ├── utils/               # Helper functions 
│   ├── App.jsx              # Root component 
│   ├── main.jsx             # Application entry point 
│   └── NotFound.jsx         # 404 page 
├── components.json          # shadcn/ui configuration 
├── tailwind.config.js       # Tailwind CSS configuration 
├── package.json             # Project configuration 
├── vite.config.js           # Vite configuration 
└── netlify.toml             # Deployment configuration 
```

## 🧩 Core Modules

### 🎯 Components (src/components/)
**Purpose**: Reusable UI components built with shadcn/ui and Tailwind CSS

**shadcn/ui Components** (src/components/ui/):
- Button, Input, Card, Dialog 
- Select, Checkbox, RadioGroup 
- Table, Badge, Alert 
- Tooltip, Popover, Sheet 
- Progress, Separator, Skeleton 
- And other shadcn/ui primitives 

**Custom Components**:
- Navbar.jsx - Application navigation with shadcn/ui components 
- Footer.jsx - Site footer 
- HeroSection.jsx - Landing page hero with modern design 
- MetricsGrid.jsx - Data visualization grid using Card components 
- PerformanceCharts.jsx - Chart components with shadcn/ui integration 
- PortfolioAnalytics.jsx - Portfolio analysis using Table and Badge 
- ResultsDashboard.jsx - Results overview with Card layouts 
- FilteringSystem.jsx - Data filtering with Select and Input 
- RankingSystem.jsx - Ranking displays using Table components 
- ConfigurationPanel.jsx - Settings interface with Form controls 
- ExportSection.jsx - Data export with Button and Dialog 
- StrategyTemplates.jsx - Trading strategy templates using Card grid 

### 📄 Pages (src/pages/)
**Purpose**: Main application views with consistent shadcn/ui styling

- **Home** (home/) - Landing page with modern hero and dashboard cards 
- **Backtesting** (backtesting/) - Core backtesting functionality 
  - Form-based strategy configuration 
  - Results display with data tables 
  - Loading states with Skeleton components 

### 🎣 Hooks (src/hooks/)
**Purpose**: Custom React hooks for reusable stateful logic and shadcn/ui integrations

### 🏗️ Layout (src/layout/)
**Purpose**: Application structure using shadcn/ui layout components
- Layout.jsx - Main layout wrapper with navigation and responsive design 

### 📚 Library (src/lib/)
**Purpose**: Core utilities and shadcn/ui configuration
- axios.js - HTTP client configuration 
- utils.js - shadcn/ui utility functions (cn, clsx integration) 

## 🎨 Design System

### 🎯 Tailwind CSS Configuration
- **Custom Theme**: Extended color palette for financial data 
- **Typography**: Custom font scales for data-heavy interfaces 
- **Spacing**: Consistent spacing scale 
- **Components**: Custom component classes for financial widgets 

### ✨ shadcn/ui Integration
- **Consistent Components**: All UI elements follow shadcn/ui design patterns 
- **Accessibility**: Built-in ARIA support 
- **Theming**: Dark/light mode support with CSS variables 
- **Customization**: Tailwind-based styling for brand consistency 

## 🚀 Key Features
- **Financial Backtesting**: Test trading strategies with modern form controls 
- **Portfolio Analytics**: Comprehensive analysis using data tables and charts 
- **Data Visualization**: Interactive charts with shadcn/ui overlays and tooltips 
- **Strategy Templates**: Card-based template selection interface 
- **Export Functionality**: Dialog-based export with progress indicators 
- **Responsive Design**: Mobile-first design with shadcn/ui responsive components 
- **Modern UI/UX**: Clean, accessible interface following current design trends 

## 💡 Development Patterns
- **Component-Driven**: Modular components built on shadcn/ui primitives 
- **Custom Hooks**: Encapsulated logic with shadcn/ui state management 
- **Design System**: Consistent styling using Tailwind + shadcn/ui 
- **Accessibility-First**: WCAG compliance through shadcn/ui components 

## ⚙️ Configuration Files
- **components.json** - shadcn/ui component configuration and aliases 
- **tailwind.config.js** - Extended Tailwind configuration with custom theme 
- **vite.config.js** - Build tool configuration with path aliases 
- **eslint.config.js** - Code linting rules 
- **jsconfig.json** - JavaScript project settings with path mapping 

## 🧠 State Management
- **React Built-in**: useState for local state, useEffect for handling side effects 
- **Custom Hooks**: Shared state logic across components 

## 🎨 Styling Architecture
- **Utility-First**: Tailwind CSS for rapid development 
- **Component Library**: shadcn/ui for consistent, accessible components 
- **Custom Components**: Extended shadcn/ui components for domain-specific needs 
- **Theme System**: CSS variables for dynamic theming 
- **Responsive Design**: Mobile-first approach with Tailwind breakpoints 

## ⚡ Performance Considerations
- **Tree Shaking**: Optimized shadcn/ui component imports 
- **Bundle Optimization**: Vite's built-in optimizations