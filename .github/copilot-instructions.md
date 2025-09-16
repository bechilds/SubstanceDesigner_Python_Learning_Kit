<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

# Copilot Instructions for Substance Designer Python Scripts

This workspace is focused on Adobe Substance Designer Python scripting for beginners. When providing assistance:

## Context
- This is a beginner-friendly Python scripting project for Adobe Substance Designer
- Users may have little to no programming experience
- Focus on practical, real-world Substance Designer automation tasks
- Emphasize clear, well-commented code with explanations

## Code Style Guidelines
- Use clear, descriptive variable and function names
- Add extensive comments explaining what each section does
- Include error handling and user-friendly error messages
- Provide step-by-step explanations for complex operations
- Use Python best practices but prioritize readability over advanced techniques

## Substance Designer Specific Guidelines
- Always import the necessary SD modules at the top of scripts
- Include proper initialization of the SD application context
- Use try-catch blocks for SD API calls that might fail
- Provide examples of common node types and their properties
- Include practical examples of parameter manipulation
- Show how to work with different substance file formats (.sbs, .sbsar)

## Tutorial Structure
- Start with simple concepts and gradually increase complexity
- Include "What you'll learn" sections
- Provide both code examples and expected outcomes
- Include troubleshooting tips for common issues
- Add references to official Substance Designer documentation

## Example Patterns
- Show before/after screenshots in comments when possible
- Include both interactive and batch processing examples
- Demonstrate error handling and validation
- Provide reusable utility functions
- Include performance considerations for large operations

When generating code, always consider that the user might be running this in Substance Designer's Python environment and may need guidance on how to execute the scripts properly.
