# Problems Faced During Development

## 1. Authentication Issues
- Forgot to protect some routes with login checks.
- Session data caused bugs after logout/login.

## 2. Database Confusion
- Mixed up `user_id` and `project_id` in a few places.
- Forgot to commit changes, so data didn’t save.

## 3. File Upload Problems
- File size tracking was inconsistent.
- Storage limits were sometimes calculated wrong.

## 4. Cloudinary Setup
- Uploads failed due to missing or incorrect env variables.
- Folder structure had to be changed later.

## 5. Code Execution Bugs
- Infinite loops required adding execution timeouts.
- Temporary files were not deleted at first.

## 6. AI (Gemini) Integration
- Used the wrong model name initially.
- Large prompts sometimes broke responses.

## 7. Code Organization
- App file became too large.
- Some routes handle too many responsibilities.
