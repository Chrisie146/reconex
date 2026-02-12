Frontend OCR UI

Install new frontend dependencies:

```bash
cd frontend
npm install
# or
pnpm install
```

Run dev server:

```bash
npm run dev
```

Navigate to `/ocr` to open the Guided OCR Wizard. Upload a scanned PDF, draw regions on the canvas for Date / Description / Amount, save regions, then click "Run OCR & Preview" to call the backend and view parsed rows. The preview table highlights rows with issues for manual correction.
