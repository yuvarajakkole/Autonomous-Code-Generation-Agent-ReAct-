let display = document.getElementById('display');
let currentInput = '';

function clearDisplay() {
    currentInput = '';
    display.textContent = '0';
}

function appendNumber(number) {
    if (currentInput === '0') {
        currentInput = '';
    }
    currentInput += number;
    display.textContent = currentInput;
}

function appendOperator(operator) {
    if (currentInput === '') return;
    const lastChar = currentInput[currentInput.length - 1];
    if ('+-*/'.includes(lastChar)) {
        currentInput = currentInput.slice(0, -1);
    }
    currentInput += operator;
    display.textContent = currentInput;
}

function appendDecimal() {
    if (!currentInput.includes('.')) {
        currentInput += '.';
        display.textContent = currentInput;
    }
}

function calculate() {
    try {
        if (currentInput.includes('/0')) {
            throw new Error('Division by zero');
        }
        const result = eval(currentInput);
        display.textContent = result;
        currentInput = result.toString();
    } catch (error) {
        display.textContent = 'Error';
        currentInput = '';
    }
}